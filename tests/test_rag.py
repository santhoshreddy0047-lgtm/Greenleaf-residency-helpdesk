from src.retrieve import retrieve_documents
from src.answer import answer_question


def test_pool_timings():
    question = "What are the swimming pool timings?"

    results = retrieve_documents(question)

    assert results, "Pool question should retrieve documents."

    sources = [
        result.payload.get("source")
        for result in results
    ]

    assert "Facilities_Guide.md" in sources


def test_not_found_question():
    question = "What is the Clubhouse Wi-Fi password?"

    results = retrieve_documents(question)

    assert not results, (
        "Unknown question should not retrieve "
        "relevant documents."
    )


def test_gym_conflict():
    question = "What are the gym timings?"

    result = answer_question(question)

    answer = result["answer"].lower()

    assert "5:30" in answer
    assert "10:30" in answer


def test_current_maintenance():
    question = (
        "What is the monthly maintenance "
        "charge for a 2BHK flat?"
    )

    result = answer_question(question)

    answer = result["answer"]

    assert "2,800" in answer or "2800" in answer


def test_sources_are_application_generated():
    question = "What are the swimming pool timings?"

    result = answer_question(question)

    answer = result["answer"]

    assert "[Source" not in answer
    assert len(result["sources"]) > 0


if __name__ == "__main__":

    print("Running GreenLeaf RAG tests...")
    print()

    test_pool_timings()
    print("PASS: Pool timings")

    test_not_found_question()
    print("PASS: Not-found question")

    test_gym_conflict()
    print("PASS: Gym conflict")

    test_current_maintenance()
    print("PASS: Maintenance update")

    test_sources_are_application_generated()
    print("PASS: Source separation")

    print()
    print("All tests passed.")