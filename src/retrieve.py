from datetime import date

from qdrant_client import QdrantClient
from fastembed import TextEmbedding

from src.build_index import (
    COLLECTION_NAME,
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL,
)
from src.config import QDRANT_DATA_DIR


TOP_K = 5
SIMILARITY_THRESHOLD = 0.45


def _effective_date_sort_key(result):
    effective_date = (result.payload or {}).get("effective_date")
    try:
        return date.fromisoformat(effective_date)
    except (TypeError, ValueError):
        return date.min


def retrieve_documents(question: str, top_k: int = TOP_K):
    if not question.strip() or top_k <= 0:
        return []

    model = TextEmbedding(model_name=EMBEDDING_MODEL)
    query_embeddings = list(model.query_embed([question]))
    if len(query_embeddings) != 1:
        raise RuntimeError("FastEmbed did not return one query vector.")

    query_embedding = [float(value) for value in query_embeddings[0]]
    if len(query_embedding) != EMBEDDING_DIMENSION:
        raise RuntimeError("FastEmbed returned an unexpected query dimension.")

    client = QdrantClient(path=str(QDRANT_DATA_DIR))

    try:
        point_count = client.count(
            collection_name=COLLECTION_NAME,
            exact=True,
        ).count
        if not point_count:
            return []

        # Examine every indexed candidate so a current dated notice is not
        # excluded merely because older chunks occupy the nearest top-k slots.
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_embedding,
            limit=max(point_count, top_k),
            with_payload=True,
        )

        relevant_results = [
            result
            for result in results.points
            if result.score >= SIMILARITY_THRESHOLD
        ]
        relevant_results.sort(
            key=lambda result: (
                _effective_date_sort_key(result),
                result.score,
            ),
            reverse=True,
        )
        return relevant_results[:top_k]
    finally:
        client.close()


if __name__ == "__main__":

    question = input("Enter your question: ").strip()

    if not question:
        print("Please enter a question.")
        raise SystemExit

    results = retrieve_documents(question)

    print()
    print("=" * 60)
    print("RETRIEVED DOCUMENTS")
    print("=" * 60)

    if not results:
        print("No relevant documents found.")
        raise SystemExit

    for index, result in enumerate(results, start=1):

        payload = result.payload or {}

        print()
        print(f"Result {index}")
        print(f"Score          : {result.score:.4f}")
        print(f"Source         : {payload.get('source', 'unknown')}")
        print(f"Page           : {payload.get('page', 1)}")
        print(f"Section        : {payload.get('section', 'General')}")
        print(f"Effective date : {payload.get('effective_date', 'Unknown')}")

        print("-" * 60)