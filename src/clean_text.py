import re


def clean_text(text: str) -> str:
    """
    Clean unnecessary whitespace and blank lines.
    """

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove trailing spaces
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)

    # Collapse multiple spaces/tabs
    text = re.sub(r"[ \t]{2,}", " ", text)

    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def mask_sensitive_data(text: str) -> tuple[str, dict]:
    """
    Replace sensitive personal information before the text
    can be sent to the LLM.
    """

    counts = {
        "phone": 0,
        "email": 0,
        "pan": 0,
        "aadhaar": 0,
    }

    # Phone numbers:
    # 9876543210
    # +91 98765 43210
    # 98765-43210
    phone_pattern = re.compile(
        r"(?<!\d)"
        r"(?:\+91[\s-]?)?"
        r"\d{5}[\s-]?\d{5}"
        r"(?!\d)"
    )

    text, counts["phone"] = phone_pattern.subn("[PHONE]", text)

    # Email addresses
    email_pattern = re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    )

    text, counts["email"] = email_pattern.subn("[EMAIL]", text)

    # PAN
    pan_pattern = re.compile(
        r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
        re.IGNORECASE,
    )

    text, counts["pan"] = pan_pattern.subn("[PAN]", text)

    # Aadhaar
    aadhaar_pattern = re.compile(
        r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)"
    )

    text, counts["aadhaar"] = aadhaar_pattern.subn(
        "[AADHAAR]",
        text,
    )

    return text, counts


if __name__ == "__main__":
    sample = """
    Resident phone: 9876543210
    Email: resident@example.com
    PAN: ABCDE1234F
    Aadhaar: 1234 5678 9012
    """

    cleaned = clean_text(sample)
    protected, counts = mask_sensitive_data(cleaned)

    print(protected)
    print()
    print("Privacy counts:")
    print(counts)