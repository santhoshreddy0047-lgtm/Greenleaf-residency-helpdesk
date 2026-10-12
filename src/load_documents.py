from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
)

from src.config import RAW_DATA_DIR
from src.clean_text import clean_text, mask_sensitive_data


EXCLUDED_RAW_DOCUMENT = "GreenLeaf_Residency_Helpdesk_RAG_Project (1).pdf"


def load_documents():
    documents = []

    for file_path in sorted(RAW_DATA_DIR.iterdir()):
        if not file_path.is_file():
            continue

        if file_path.name == EXCLUDED_RAW_DOCUMENT:
            continue

        extension = file_path.suffix.lower()

        try:
            if extension == ".pdf":
                loader = PyPDFLoader(str(file_path))

            elif extension == ".docx":
                loader = Docx2txtLoader(str(file_path))

            elif extension in [".md", ".txt"]:
                loader = TextLoader(
                    str(file_path),
                    encoding="utf-8",
                )

            else:
                print(f"Skipped unsupported file: {file_path.name}")
                continue

            loaded = loader.load()

            file_counts = {
                "phone": 0,
                "email": 0,
                "pan": 0,
                "aadhaar": 0,
            }

            for document in loaded:
                # Clean the document text
                text = clean_text(document.page_content)

                # Mask sensitive information
                text, counts = mask_sensitive_data(text)

                document.page_content = text

                # Preserve source metadata
                document.metadata["source"] = file_path.name

                # PDF pages are zero-based in PyPDFLoader
                if extension == ".pdf":
                    page = document.metadata.get("page")

                    document.metadata["page"] = (
                        page + 1 if isinstance(page, int) else 1
                    )
                else:
                    document.metadata["page"] = 1

                # Add privacy counts for this file
                for key in file_counts:
                    file_counts[key] += counts[key]

                documents.append(document)

            print(f"Loaded: {file_path.name}")
            print(f"  Parts: {len(loaded)}")
            print(f"  Privacy: {file_counts}")

        except Exception as error:
            print(
                f"Failed to load {file_path.name} "
                f"({type(error).__name__})."
            )

    return documents


if __name__ == "__main__":
    documents = load_documents()

    print()
    print("=" * 50)
    print(f"Total document parts loaded: {len(documents)}")
    print("=" * 50)