from pathlib import Path

from src.build_index import index_documents
from src.chunk_text import chunk_documents
from src.config import UPDATES_DATA_DIR
from src.load_documents import load_documents


def load_update_documents():
    """
    Load documents from data/updates/ using the same
    cleaning and privacy masking pipeline as raw documents.
    """

    # Temporarily reuse the existing loader by creating
    # a small list of supported update files manually.
    from langchain_community.document_loaders import (
        PyPDFLoader,
        TextLoader,
        Docx2txtLoader,
    )

    from src.clean_text import clean_text, mask_sensitive_data

    documents = []

    for file_path in sorted(UPDATES_DATA_DIR.iterdir()):

        if not file_path.is_file():
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
                    encoding="utf-8"
                )

            else:
                print(
                    f"Skipped unsupported file: {file_path.name}"
                )
                continue

            loaded = loader.load()

            file_counts = {
                "phone": 0,
                "email": 0,
                "pan": 0,
                "aadhaar": 0,
            }

            for document in loaded:

                text = clean_text(
                    document.page_content
                )

                text, counts = mask_sensitive_data(
                    text
                )

                document.page_content = text

                document.metadata["source"] = (
                    file_path.name
                )

                if extension == ".pdf":

                    page = document.metadata.get(
                        "page"
                    )

                    document.metadata["page"] = (
                        page + 1
                        if isinstance(page, int)
                        else 1
                    )

                else:
                    document.metadata["page"] = 1

                for key in file_counts:
                    file_counts[key] += counts[key]

                documents.append(document)

            print(
                f"Loaded update: {file_path.name}"
            )

            print(
                f"  Parts: {len(loaded)}"
            )

            print(
                f"  Privacy: {file_counts}"
            )

        except Exception as error:

            print(
                f"Failed to load update "
                f"{file_path.name}: {error}"
            )

    return documents


def main():

    print("Loading update documents...")

    documents = load_update_documents()

    print()

    print(
        f"Update document parts loaded: {len(documents)}"
    )

    if not documents:
        print("No update documents found.")
        return

    print()

    print("Indexing update documents...")

    index_documents(documents)


if __name__ == "__main__":
    main()