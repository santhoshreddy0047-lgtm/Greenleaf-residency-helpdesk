from types import SimpleNamespace

import pytest
from langchain_core.documents import Document
from qdrant_client.models import PointStruct

from src import answer, build_index, load_documents, retrieve


class FakeEmbedding:
    models = []
    document_batches = []
    query_batches = []

    def __init__(self, model_name):
        self.models.append(model_name)

    def embed(self, documents):
        documents = list(documents)
        self.document_batches.append(documents)
        for document in documents:
            yield [float(len(document))] + [0.0] * 383

    def query_embed(self, queries):
        queries = list(queries)
        self.query_batches.append(queries)
        for _ in queries:
            yield [0.25] * 384


class FakeQdrant:
    def __init__(self, points=None, query_points=None):
        self.points = {
            point.id: point for point in (points or [])
        }
        self.query_results = query_points or []
        self.last_query = None
        self.closed = False

    def get_collections(self):
        return SimpleNamespace(
            collections=[
                SimpleNamespace(name=build_index.COLLECTION_NAME)
            ]
        )

    def scroll(self, collection_name, scroll_filter, **kwargs):
        source = scroll_filter.must[0].match.value
        records = [
            SimpleNamespace(id=point.id)
            for point in self.points.values()
            if point.payload.get("source") == source
        ]
        return records, None

    def upsert(self, collection_name, points):
        self.points.update({point.id: point for point in points})

    def delete(self, collection_name, points_selector):
        for point_id in points_selector:
            self.points.pop(point_id, None)

    def get_collection(self, collection_name):
        return SimpleNamespace(points_count=len(self.points))

    def count(self, collection_name, exact):
        return SimpleNamespace(count=len(self.query_results))

    def query_points(self, **kwargs):
        self.last_query = kwargs
        return SimpleNamespace(points=self.query_results)

    def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def reset_embedding_calls():
    FakeEmbedding.models = []
    FakeEmbedding.document_batches = []
    FakeEmbedding.query_batches = []


def document(text, source, effective_date=None):
    return Document(
        page_content=text,
        metadata={
            "source": source,
            "page": 1,
            "section": "Maintenance",
            "effective_date": effective_date,
        },
    )


def test_fastembed_indexes_384_float_vectors_and_replaces_sources(monkeypatch):
    store = FakeQdrant()
    monkeypatch.setattr(build_index, "TextEmbedding", FakeEmbedding)
    monkeypatch.setattr(build_index, "chunk_documents", lambda docs: docs)
    monkeypatch.setattr(build_index, "create_client", lambda: store)

    build_index.index_documents(
        [
            document("old maintenance", "maintenance.docx", "2025-01-01"),
            document("pool schedule", "facilities.md"),
        ]
    )
    build_index.index_documents(
        [document("revised maintenance", "maintenance.docx", "2026-04-01")]
    )

    assert FakeEmbedding.models == [
        build_index.EMBEDDING_MODEL,
        build_index.EMBEDDING_MODEL,
    ]
    assert FakeEmbedding.document_batches == [
        ["old maintenance", "pool schedule"],
        ["revised maintenance"],
    ]
    assert len(store.points) == 2
    assert {
        point.payload["source"] for point in store.points.values()
    } == {"maintenance.docx", "facilities.md"}
    assert all(
        len(point.vector) == build_index.EMBEDDING_DIMENSION == 384
        and all(isinstance(value, float) for value in point.vector)
        for point in store.points.values()
    )
    assert next(
        point.payload for point in store.points.values()
        if point.payload["source"] == "maintenance.docx"
    )["text"] == "revised maintenance"


def test_empty_documents_and_chunks_do_not_load_models_or_qdrant(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("No model or database should be initialized.")

    monkeypatch.setattr(build_index, "TextEmbedding", unexpected)
    monkeypatch.setattr(build_index, "create_client", unexpected)
    build_index.index_documents([])

    monkeypatch.setattr(build_index, "chunk_documents", lambda docs: [])
    build_index.index_documents([document("content", "source.txt")])


def test_build_removes_previously_indexed_assignment_pdf(monkeypatch):
    assignment_point = PointStruct(
        id=11,
        vector=[0.0] * 384,
        payload={
            "source": load_documents.EXCLUDED_RAW_DOCUMENT,
            "text": "assignment material",
        },
    )
    store = FakeQdrant([assignment_point])
    monkeypatch.setattr(
        build_index,
        "load_documents",
        lambda: [document("residency facts", "facilities.md")],
    )
    monkeypatch.setattr(build_index, "TextEmbedding", FakeEmbedding)
    monkeypatch.setattr(build_index, "chunk_documents", lambda docs: docs)
    monkeypatch.setattr(build_index, "create_client", lambda: store)

    build_index.build_index()

    assert all(
        point.payload["source"] != load_documents.EXCLUDED_RAW_DOCUMENT
        for point in store.points.values()
    )
    assert any(
        point.payload["source"] == "facilities.md"
        for point in store.points.values()
    )


def test_embedding_failure_retains_previous_points_and_reports_safe_error(
    monkeypatch, capsys
):
    old_point = PointStruct(
        id=7,
        vector=[0.0] * 384,
        payload={"source": "maintenance.docx", "text": "old text"},
    )
    store = FakeQdrant([old_point])

    class FailedEmbedding:
        def __init__(self, model_name):
            pass

        def embed(self, documents):
            raise ValueError("private-value-9876543210")

    monkeypatch.setattr(build_index, "TextEmbedding", FailedEmbedding)
    monkeypatch.setattr(build_index, "chunk_documents", lambda docs: docs)
    monkeypatch.setattr(build_index, "create_client", lambda: store)

    with pytest.raises(RuntimeError, match="existing indexed chunks were retained"):
        build_index.index_documents(
            [document("replacement", "maintenance.docx")]
        )

    assert list(store.points) == [7]
    assert "private-value-9876543210" not in capsys.readouterr().out


def test_retrieval_uses_same_fastembed_model_threshold_and_top_k(monkeypatch):
    points = [
        SimpleNamespace(
            payload={"source": "old.docx", "effective_date": "2025-01-01"},
            score=0.81,
        ),
        SimpleNamespace(
            payload={"source": "revision.docx", "effective_date": "2026-04-01"},
            score=0.45,
        ),
        SimpleNamespace(
            payload={"source": "irrelevant.docx", "effective_date": "2027-01-01"},
            score=0.449,
        ),
    ]
    store = FakeQdrant(query_points=points)
    monkeypatch.setattr(retrieve, "TextEmbedding", FakeEmbedding)
    monkeypatch.setattr(retrieve, "QdrantClient", lambda **kwargs: store)

    results = retrieve.retrieve_documents("current 2BHK maintenance", top_k=2)

    assert FakeEmbedding.models == [build_index.EMBEDDING_MODEL]
    assert FakeEmbedding.query_batches == [["current 2BHK maintenance"]]
    assert len(store.last_query["query"]) == 384
    assert all(isinstance(value, float) for value in store.last_query["query"])
    assert store.last_query["limit"] == 3
    assert [result.payload["source"] for result in results] == [
        "revision.docx",
        "old.docx",
    ]
    assert all(result.score >= retrieve.SIMILARITY_THRESHOLD for result in results)
    assert store.closed


def test_answer_abstains_and_does_not_call_groq_when_no_results(monkeypatch):
    def unexpected_groq(*args, **kwargs):
        raise AssertionError("Groq must not be initialized without evidence.")

    monkeypatch.setattr(answer, "retrieve_documents", lambda question: [])
    monkeypatch.setattr(answer, "Groq", unexpected_groq)

    result = answer.answer_question("What is the Wi-Fi password?")

    assert "couldn't find" in result["answer"]
    assert result["sources"] == []


def test_maintenance_answer_uses_newer_evidence_and_citations(monkeypatch):
    retrieved = [
        SimpleNamespace(
            score=0.51,
            payload={
                "text": "Original 2BHK monthly maintenance: 2,500.",
                "source": "Schedule_of_Charges_2025.pdf",
                "page": 3,
                "section": "Maintenance",
                "effective_date": "2025-01-01",
            },
        ),
        SimpleNamespace(
            score=0.47,
            payload={
                "text": (
                    "Revised 2BHK monthly maintenance: 2,800. "
                    "Effective date: 1 April 2026. Late payment charge: 150."
                ),
                "source": "Notice_2026-02-20_Maintenance_Revision.docx",
                "page": 1,
                "section": "Maintenance",
                "effective_date": "2026-04-01",
            },
        ),
    ]
    captured = {}

    class FakeGroq:
        def __init__(self, api_key):
            assert api_key == "test-key"

        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    captured["messages"] = kwargs["messages"]
                    message = SimpleNamespace(
                        content=(
                            "The revised monthly charge is ₹2,800 from "
                            "1 April 2026; the newer notice applies. "
                            "The late-payment charge is ₹150."
                        )
                    )
                    return SimpleNamespace(
                        choices=[SimpleNamespace(message=message)]
                    )

    monkeypatch.setattr(answer, "retrieve_documents", lambda question: retrieved)
    monkeypatch.setattr(answer, "Groq", FakeGroq)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    result = answer.answer_question(
        "What is the current 2BHK monthly maintenance charge?"
    )

    prompt = captured["messages"][1]["content"]
    assert prompt.index("Notice_2026-02-20_Maintenance_Revision.docx") < prompt.index(
        "Schedule_of_Charges_2025.pdf"
    )
    assert "2,800" in result["answer"]
    assert "1 April 2026" in result["answer"]
    assert "newer notice applies" in result["answer"]
    assert "150" in result["answer"]
    assert result["sources"][0] == {
        "source": "Notice_2026-02-20_Maintenance_Revision.docx",
        "page": 1,
        "section": "Maintenance",
        "effective_date": "2026-04-01",
    }
    assert len(result["sources"]) == 2
    assert "[Source" not in result["answer"]


def test_masks_pii_in_question_context_and_generated_answer_before_groq(
    monkeypatch,
):
    retrieved = [
        SimpleNamespace(
            score=0.9,
            payload={
                "text": (
                    "Contact 9876543210, resident@example.com, "
                    "PAN ABCDE1234F, Aadhaar 1234 5678 9012."
                ),
                "source": "resident-notice.txt",
                "page": 2,
                "section": "Contact",
                "effective_date": None,
            },
        )
    ]
    captured = {}

    class FakeGroq:
        def __init__(self, api_key):
            pass

        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    captured["prompt"] = kwargs["messages"][1]["content"]
                    message = SimpleNamespace(
                        content=(
                            "Phone 9876543210, email resident@example.com, "
                            "PAN ABCDE1234F, Aadhaar 1234 5678 9012."
                        )
                    )
                    return SimpleNamespace(
                        choices=[SimpleNamespace(message=message)]
                    )

    monkeypatch.setattr(answer, "retrieve_documents", lambda question: retrieved)
    monkeypatch.setattr(answer, "Groq", FakeGroq)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    result = answer.answer_question(
        "Please check 9876543210 and resident@example.com"
    )

    for sensitive_value in (
        "9876543210",
        "resident@example.com",
        "ABCDE1234F",
        "1234 5678 9012",
    ):
        assert sensitive_value not in captured["prompt"]
        assert sensitive_value not in result["answer"]
    assert all(
        marker in captured["prompt"]
        for marker in ("[PHONE]", "[EMAIL]", "[PAN]", "[AADHAAR]")
    )


def test_raw_loader_masks_pii_and_skips_assignment_pdf(monkeypatch, tmp_path, capsys):
    (tmp_path / "private.pdf").touch()
    assignment = tmp_path / load_documents.EXCLUDED_RAW_DOCUMENT
    assignment.touch()
    loaded_paths = []

    class FakePDFLoader:
        def __init__(self, path):
            loaded_paths.append(path)

        def load(self):
            return [
                Document(
                    page_content=(
                        "9876543210 resident@example.com ABCDE1234F "
                        "1234 5678 9012"
                    ),
                    metadata={"page": 0},
                )
            ]

    monkeypatch.setattr(load_documents, "RAW_DATA_DIR", tmp_path)
    monkeypatch.setattr(load_documents, "PyPDFLoader", FakePDFLoader)

    documents = load_documents.load_documents()
    output = capsys.readouterr().out

    assert len(documents) == 1
    assert documents[0].metadata["page"] == 1
    assert documents[0].metadata["source"] == "private.pdf"
    assert loaded_paths == [str(tmp_path / "private.pdf")]
    assert all(
        marker in documents[0].page_content
        for marker in ("[PHONE]", "[EMAIL]", "[PAN]", "[AADHAAR]")
    )
    assert all(
        value not in output
        for value in (
            "9876543210",
            "resident@example.com",
            "ABCDE1234F",
            "1234 5678 9012",
        )
    )


def test_maintenance_update_effective_date_is_extracted():
    from src.chunk_text import extract_effective_date

    assert extract_effective_date("Effective date: 1 April 2026") == "2026-04-01"
