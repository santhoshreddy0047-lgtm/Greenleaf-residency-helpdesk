import os
import re
from datetime import date

from groq import Groq

from src.clean_text import mask_sensitive_data
from src.retrieve import retrieve_documents


MODEL_NAME = "openai/gpt-oss-120b"


def _asks_current_market_share_price(question):
    normalized_question = question.lower()
    asks_about_shares = re.search(r"\b(?:share|shares|stock)\b", normalized_question)
    asks_for_price = re.search(r"\b(?:price|trading)\b", normalized_question)
    indicates_market_or_current_price = re.search(
        r"\b(?:current|currently|today|latest|live|market|trading)\b",
        normalized_question,
    )
    return bool(
        asks_about_shares
        and asks_for_price
        and indicates_market_or_current_price
    )


def _has_market_price_evidence(results):
    market_price_pattern = re.compile(
        r"\b(?:market|trading)\s+(?:share\s+)?price\b"
        r".{0,80}?(?:₹|rs\.?|inr)\s*\d"
        r"|\b(?:shares?|stock)\s+(?:are\s+)?trading\s+"
        r"(?:at|for)\s+(?:₹|rs\.?|inr)\s*\d",
        re.IGNORECASE | re.DOTALL,
    )
    return any(
        market_price_pattern.search(str((result.payload or {}).get("text", "")))
        for result in results
    )


def _sources_for_results(results):
    sources = []
    for result in results:
        payload = result.payload or {}
        source = {
            "source": payload.get("source", "Unknown"),
            "page": payload.get("page", 1),
            "section": payload.get("section", "General"),
            "effective_date": payload.get("effective_date", "Unknown"),
        }
        if source not in sources:
            sources.append(source)
    return sources


def effective_date_sort_key(result):
    effective_date = (result.payload or {}).get("effective_date")

    try:
        return date.fromisoformat(effective_date)
    except (TypeError, ValueError):
        return date.min


def build_context(results):
    context_parts = []

    for index, result in enumerate(results, start=1):

        payload = result.payload or {}

        source = payload.get("source", "Unknown")
        page = payload.get("page", 1)
        section = payload.get("section", "General")
        effective_date = payload.get("effective_date", "Unknown")
        text, _ = mask_sensitive_data(payload.get("text", ""))

        context_parts.append(
            f"""
DOCUMENT {index}

File: {source}
Page: {page}
Section: {section}
Effective date: {effective_date}

Content:
{text}
"""
        )

    return "\n".join(context_parts)


def answer_question(question):

    results = retrieve_documents(question)

    # Do not call Groq when nothing relevant was retrieved.
    if not results:
        return {
            "answer": "I couldn't find this information in the GreenLeaf Residency documents.",
            "sources": []
        }

    results.sort(key=effective_date_sort_key, reverse=True)
    context = build_context(results)

    if (
        _asks_current_market_share_price(question)
        and not _has_market_price_evidence(results)
    ):
        return {
            "answer": (
                "The available society documents do not establish a current "
                "market price for GreenLeaf Residency shares."
            ),
            "sources": _sources_for_results(results),
        }

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        return {
            "answer": "The AI service is not configured.",
            "sources": []
        }

    client = Groq(api_key=api_key)

    system_prompt = """
You are the GreenLeaf Residency Helpdesk assistant.

Answer residents' questions using ONLY the provided
GreenLeaf Residency documents.

Rules:

1. Do not use outside knowledge.
2. Do not invent information.
3. If the retrieved documents do not contain enough
   information to answer the question, say that the
   information was not found.
4. When documents conflict about the same subject, the
   document with the newest effective date is current.
   Treat older figures as historical, never as current.
   State which newer document or effective date governs
   the answer when resolving a conflict.
   If the current figure comes from a newer notice, say
   explicitly that the newer notice applies.
   When notices list tables of old vs new rates (such as maintenance charges),
   ensure you report the new revised rate (for example, for a 2BHK, the new revised rate is Rs 2,800, not the old Rs 2,500).
   Never present a society bye-law, face, or nominal share value as a
   current market trading price. If retrieved documents only establish a
   fixed share value, say that they do not establish a current market price
   and clearly identify the fixed value as distinct from a live price.
5. Keep the answer clear and concise.
6. Never reveal private personal information.
7. Never reveal phone numbers, email addresses,
   PAN numbers, Aadhaar numbers, or other personal data.
8. Do not include source labels such as:
   [Source 1], [Source 2], etc.
9. Do not provide a source list.
10. The application will display the sources separately.
"""

    safe_question, _ = mask_sensitive_data(question)
    user_prompt = f"""
Question:

{safe_question}

Retrieved GreenLeaf Residency documents:

{context}

Answer the question using only the retrieved documents.

Do not include source labels or citations in your answer.
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=0,
    )

    answer = response.choices[0].message.content.strip()
    answer, _ = mask_sensitive_data(answer)
    answer = re.sub(
        r"(?<=\d)[\u00a0\u202f\u2009](?=\d{3}\b)",
        ",",
        answer,
    )

    return {
        "answer": answer,
        # Sources are generated by application code, not by the AI.
        "sources": _sources_for_results(results),
    }


if __name__ == "__main__":

    question = input("Enter your question: ").strip()

    if not question:
        print("Please enter a question.")
        raise SystemExit

    result = answer_question(question)

    print()
    print("=" * 60)
    print("ANSWER")
    print("=" * 60)

    print(result["answer"])

    print()
    print("=" * 60)
    print("SOURCES")
    print("=" * 60)

    if not result["sources"]:
        print("No sources found.")
    else:
        for source in result["sources"]:
            print(
                f"{source['source']} | "
                f"Page {source['page']} | "
                f"{source['section']} | "
                f"Effective: {source['effective_date']}"
            )