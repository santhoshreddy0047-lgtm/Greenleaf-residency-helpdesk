from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from src.build_index import COLLECTION_NAME, EMBEDDING_MODEL
from src.config import QDRANT_DATA_DIR


TOP_K = 5
SIMILARITY_THRESHOLD = 0.45


def retrieve_documents(question: str, top_k: int = TOP_K):
    client = QdrantClient(path=str(QDRANT_DATA_DIR))

    model = SentenceTransformer(EMBEDDING_MODEL)

    query_embedding = model.encode(
        question,
        normalize_embeddings=True
    )

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding.tolist(),
        limit=top_k,
        with_payload=True,
    )

    client.close()

    relevant_results = [
        result
        for result in results.points
        if result.score >= SIMILARITY_THRESHOLD
    ]

    return relevant_results


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

        print("Text:")
        print(payload.get("text", "")[:500])

        print("-" * 60)