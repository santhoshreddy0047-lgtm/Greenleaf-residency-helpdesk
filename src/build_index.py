import hashlib

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)
from sentence_transformers import SentenceTransformer

from src.chunk_text import chunk_documents
from src.config import QDRANT_DATA_DIR
from src.load_documents import load_documents


COLLECTION_NAME = "greenleaf_residency"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def create_client():
    QDRANT_DATA_DIR.mkdir(parents=True, exist_ok=True)

    return QdrantClient(
        path=str(QDRANT_DATA_DIR)
    )


def create_collection(client, vector_size):

    collections = client.get_collections().collections

    existing_names = {
        collection.name
        for collection in collections
    }

    if COLLECTION_NAME not in existing_names:

        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )


def create_point_id(document, index):

    source = document.metadata.get(
        "source",
        "unknown"
    )

    page = document.metadata.get(
        "page",
        1
    )

    text = document.page_content

    raw_id = (
        f"{source}|"
        f"{page}|"
        f"{index}|"
        f"{text}"
    )

    hash_value = hashlib.sha256(
        raw_id.encode("utf-8")
    ).hexdigest()

    return int(
        hash_value[:16],
        16
    )


def delete_source_chunks(client, source):

    try:

        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="source",
                        match=MatchValue(
                            value=source
                        ),
                    )
                ]
            ),
        )

        print(
            f"Deleted existing chunks for: {source}"
        )

    except Exception as error:

        print(
            f"Could not delete existing chunks for "
            f"{source}: {error}"
        )


def index_documents(documents):

    if not documents:
        print("No documents to index.")
        return

    chunks = chunk_documents(documents)

    if not chunks:
        print("No chunks created.")
        return

    print(
        f"Chunks created: {len(chunks)}"
    )

    print()
    print("Loading embedding model...")

    model = SentenceTransformer(
        EMBEDDING_MODEL
    )

    texts = [
        chunk.page_content
        for chunk in chunks
    ]

    print()
    print("Creating embeddings...")

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    vector_size = len(
        embeddings[0]
    )

    client = create_client()

    create_collection(
        client,
        vector_size
    )

    sources = {
        chunk.metadata.get(
            "source",
            "unknown"
        )
        for chunk in chunks
    }

    print()

    for source in sources:

        delete_source_chunks(
            client,
            source
        )

    print()
    print("Preparing Qdrant points...")

    points = []

    for index, (chunk, embedding) in enumerate(
        zip(chunks, embeddings)
    ):

        point_id = create_point_id(
            chunk,
            index
        )

        payload = {
            "text": chunk.page_content,
            "source": chunk.metadata.get(
                "source",
                "unknown"
            ),
            "page": chunk.metadata.get(
                "page",
                1
            ),
            "section": chunk.metadata.get(
                "section",
                "General"
            ),
            "effective_date": chunk.metadata.get(
                "effective_date"
            ),
        }

        points.append(
            PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload=payload,
            )
        )

    print(
        f"Uploading {len(points)} chunks to Qdrant..."
    )

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
    )

    collection_info = client.get_collection(
        COLLECTION_NAME
    )

    print()
    print("=" * 60)
    print("QDRANT INDEXING COMPLETED")
    print("=" * 60)

    print(
        f"Collection : {COLLECTION_NAME}"
    )

    print(
        f"Points     : {collection_info.points_count}"
    )

    print("=" * 60)

    client.close()


def build_index():

    print("Loading GreenLeaf documents...")

    documents = load_documents()

    print()
    print(
        f"Document parts loaded: {len(documents)}"
    )

    print()

    index_documents(documents)


if __name__ == "__main__":

    build_index()