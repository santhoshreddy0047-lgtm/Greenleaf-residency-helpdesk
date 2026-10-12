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
from fastembed import TextEmbedding

from src.chunk_text import chunk_documents
from src.config import QDRANT_DATA_DIR
from src.load_documents import EXCLUDED_RAW_DOCUMENT, load_documents


COLLECTION_NAME = "greenleaf_residency"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384
EMBEDDING_FAILURE_MESSAGE = (
    "Embedding generation failed; existing indexed chunks were retained."
)


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


def get_source_point_ids(client, source):
    point_ids = set()
    offset = None

    while True:
        records, offset = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="source",
                        match=MatchValue(value=source),
                    )
                ]
            ),
            limit=256,
            offset=offset,
            with_payload=False,
        )
        point_ids.update(record.id for record in records)
        if offset is None:
            break

    return point_ids


def delete_source_chunks(client, source):
    point_ids = get_source_point_ids(client, source)
    if point_ids:
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=list(point_ids),
        )


def replace_source_chunks(client, source, points):
    existing_ids = get_source_point_ids(client, source)

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
    )

    stale_ids = existing_ids - {point.id for point in points}
    if stale_ids:
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=list(stale_ids),
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

    texts = [
        chunk.page_content
        for chunk in chunks
    ]

    print()
    print("Creating embeddings...")

    try:
        model = TextEmbedding(model_name=EMBEDDING_MODEL)
        embeddings = [
            [float(value) for value in embedding]
            for embedding in model.embed(texts)
        ]
        if (
            len(embeddings) != len(chunks)
            or any(
                len(embedding) != EMBEDDING_DIMENSION
                for embedding in embeddings
            )
        ):
            raise ValueError("Unexpected embedding count or dimensions.")
    except Exception:
        print(EMBEDDING_FAILURE_MESSAGE)
        raise RuntimeError(EMBEDDING_FAILURE_MESSAGE) from None

    points_by_source = {}
    source_indices = {}

    for chunk, embedding in zip(chunks, embeddings):
        source = chunk.metadata.get("source", "unknown")
        source_index = source_indices.get(source, 0)
        source_indices[source] = source_index + 1

        payload = {
            "text": chunk.page_content,
            "source": source,
            "page": chunk.metadata.get("page", 1),
            "section": chunk.metadata.get("section", "General"),
            "effective_date": chunk.metadata.get("effective_date"),
        }
        points_by_source.setdefault(source, []).append(
            PointStruct(
                id=create_point_id(chunk, source_index),
                vector=embedding,
                payload=payload,
            )
        )

    client = create_client()

    try:
        create_collection(client, EMBEDDING_DIMENSION)

        total_points = sum(
            len(points) for points in points_by_source.values()
        )
        print(f"Uploading {total_points} chunks to Qdrant...")

        for source, points in points_by_source.items():
            replace_source_chunks(client, source, points)

        collection_info = client.get_collection(COLLECTION_NAME)

        print()
        print("=" * 60)
        print("QDRANT INDEXING COMPLETED")
        print("=" * 60)
        print(f"Collection : {COLLECTION_NAME}")
        print(f"Points     : {collection_info.points_count}")
        print("=" * 60)
    finally:
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

    if not documents:
        return

    client = create_client()
    try:
        collection_names = {
            collection.name
            for collection in client.get_collections().collections
        }
        if COLLECTION_NAME in collection_names:
            delete_source_chunks(client, EXCLUDED_RAW_DOCUMENT)
    finally:
        client.close()


if __name__ == "__main__":

    build_index()