import json
from datetime import datetime
import re
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import PROCESSED_DATA_DIR
from src.load_documents import load_documents


def extract_effective_date(text: str):
    match = re.search(
        r"Effective\s+date\s*:\s*([^\n\r]+)",
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    date_text = match.group(1).strip()

    date_match = re.search(
        r"\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b",
        date_text
    )

    if date_match:
        date_text = date_match.group(0)

    formats = [
        "%d %b %Y",
        "%d %B %Y",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m-%d",
    ]

    for date_format in formats:
        try:
            return datetime.strptime(
                date_text,
                date_format
            ).date().isoformat()
        except ValueError:
            continue

    return date_text


def extract_section(text: str):
    patterns = [
        r"(?im)^(CHAPTER\s+[IVXLCDM]+[^\n]*)$",
        r"(?im)^(Item\s+\d+[^\n]*)$",
        r"(?im)^(Subject\s*:[^\n]*)$",
        r"(?im)^(Complaint\s+No[^\n]*)$",
        r"(?im)^(#{1,6}\s+.+)$",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return match.group(1).strip()

    return "General"


def save_processed_documents(documents):
    """
    Save cleaned document parts as JSON.
    Sensitive information has already been masked by load_documents().
    """

    output_dir = PROCESSED_DATA_DIR / "documents"
    output_dir.mkdir(parents=True, exist_ok=True)

    records = []

    for document in documents:
        records.append({
            "text": document.page_content,
            "metadata": document.metadata,
        })

    output_file = output_dir / "cleaned_documents.json"

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(
            records,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(f"Saved cleaned documents: {output_file}")


def save_processed_chunks(chunks):
    """
    Save generated chunks and their metadata as JSON.
    """

    output_dir = PROCESSED_DATA_DIR / "chunks"
    output_dir.mkdir(parents=True, exist_ok=True)

    records = []

    for chunk in chunks:
        records.append({
            "text": chunk.page_content,
            "metadata": chunk.metadata,
        })

    output_file = output_dir / "document_chunks.json"

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(
            records,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(f"Saved processed chunks: {output_file}")


def chunk_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150
    )

    chunks = []

    for document in documents:
        split_documents = splitter.split_documents([document])

        effective_date = extract_effective_date(
            document.page_content
        )

        section = extract_section(
            document.page_content
        )

        for chunk in split_documents:
            chunk.metadata["source"] = document.metadata.get(
                "source",
                "unknown"
            )

            chunk.metadata["page"] = document.metadata.get(
                "page",
                1
            )

            chunk.metadata["section"] = section
            chunk.metadata["effective_date"] = effective_date

            chunks.append(chunk)

    return chunks


if __name__ == "__main__":
    documents = load_documents()

    # Save cleaned document parts before chunking.
    save_processed_documents(documents)

    chunks = chunk_documents(documents)

    # Save chunks and metadata.
    save_processed_chunks(chunks)

    print()
    print("=" * 50)
    print(f"Document parts: {len(documents)}")
    print(f"Chunks created: {len(chunks)}")
    print("=" * 50)