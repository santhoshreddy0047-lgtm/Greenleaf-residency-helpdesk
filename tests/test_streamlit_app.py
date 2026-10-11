from pathlib import Path
from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")


def test_initial_render():
    """Validates that app.py loads cleanly without any runtime exception."""
    at = AppTest.from_file(APP_PATH, default_timeout=35)
    at.run()

    assert not at.exception, f"App threw exception on load: {at.exception}"
    assert at.session_state.current_question is None
    assert at.session_state.answer_result is None

    # Check that quick questions exist
    quick_keys = {"qq_pool", "qq_maint", "qq_gym", "qq_parking", "qq_pet", "qq_guest"}
    found_keys = {b.key for b in at.button if b.key}
    assert quick_keys.issubset(found_keys), f"Missing quick question buttons: {quick_keys - found_keys}"

    # Check that chat input exists
    assert at.text_input(key="chat_input_text") is not None
    print("PASS: test_initial_render")


def test_new_question_clears_answer():
    """Validates that 'Ask another question' clears the previous answer and resets state."""
    at = AppTest.from_file(APP_PATH, default_timeout=35)
    at.run()

    # Simulate existing question & answer in session state
    at.session_state.current_question = "What are the swimming pool timings?"
    at.session_state.answer_result = {
        "answer": "The pool is open from 6:00 AM to 9:00 AM.",
        "sources": [{"source": "Facilities_Guide.md", "page": 1, "section": "Pool", "effective_date": "2025-07-01"}]
    }
    at.run()

    assert not at.exception
    reset_btn = at.button(key="btn_new_question")
    assert reset_btn is not None, "Reset button should be present when answer is shown"

    # Click reset button
    reset_btn.click()
    at.run()

    assert not at.exception
    assert at.session_state.current_question is None, "Current question should be None after reset"
    assert at.session_state.answer_result is None, "Answer result should be None after reset"
    print("PASS: test_new_question_clears_answer")


def test_quick_question_pool_timings():
    """Validates that clicking the 'Pool timings' chip triggers the query."""
    at = AppTest.from_file(APP_PATH, default_timeout=45)
    at.run()

    pool_btn = at.button(key="qq_pool")
    assert pool_btn is not None
    pool_btn.click()
    at.run()

    assert not at.exception
    assert at.session_state.current_question == "What are the swimming pool timings?"
    assert at.session_state.answer_result is not None
    ans = at.session_state.answer_result["answer"].lower()
    assert "6:00" in ans or "morning" in ans
    assert len(at.session_state.answer_result["sources"]) > 0
    print("PASS: test_quick_question_pool_timings")


def test_quick_question_maintenance():
    """Validates that clicking the 'Maintenance' chip returns the revised 2,800 charge."""
    at = AppTest.from_file(APP_PATH, default_timeout=45)
    at.run()

    maint_btn = at.button(key="qq_maint")
    assert maint_btn is not None
    maint_btn.click()
    at.run()

    assert not at.exception
    assert at.session_state.answer_result is not None
    ans = at.session_state.answer_result["answer"]
    assert "2,800" in ans or "2800" in ans, f"Expected 2,800 in answer, got: {ans}"
    print("PASS: test_quick_question_maintenance (returns 2,800)")


def test_custom_question_submit():
    """Validates that typing a custom question and submitting executes RAG pipeline."""
    at = AppTest.from_file(APP_PATH, default_timeout=45)
    at.run()

    text_input = at.text_input(key="chat_input_text")
    text_input.input("What are the gym timings?")

    submit_btn = [b for b in at.button if b.label == "➤"][0]
    submit_btn.click()
    at.run()

    assert not at.exception
    assert at.session_state.answer_result is not None
    ans = at.session_state.answer_result["answer"].lower()
    assert "5:30" in ans or "10:30" in ans
    print("PASS: test_custom_question_submit")


def test_supporting_sources_rendered_as_html_cards():
    """Validates that supporting sources render as styled HTML cards without raw HTML or code blocks."""
    import markdown_it
    at = AppTest.from_file(APP_PATH, default_timeout=35)
    at.session_state.current_question = "What are the rules?"
    at.session_state.answer_result = {
        "answer": "Here are the rules.",
        "sources": [
            {
                "source": "AGM_Minutes_2025-05-25.docx",
                "page": 2,
                "section": "Rules",
                "effective_date": "2025-05-25",
            }
        ],
    }
    at.run()
    assert not at.exception

    # Find the markdown component containing the answer card
    answer_card_md = None
    for m in at.markdown:
        if '<div class="gl-answer-card">' in m.value:
            answer_card_md = m.value
            break

    assert answer_card_md is not None, "Answer card markdown should be found"
    assert "gl-source-item" in answer_card_md
    assert "AGM_Minutes_2025-05-25.docx" in answer_card_md
    assert "Page 2" in answer_card_md
    assert "Section: Rules" in answer_card_md
    assert "Effective: 2025-05-25" in answer_card_md

    # Ensure markdown-it rendering does NOT turn it into <pre><code> (raw literal code block)
    md = markdown_it.MarkdownIt()
    rendered = md.render(answer_card_md)
    assert "<pre>" not in rendered, "Supporting sources should not be wrapped in <pre> code blocks"
    assert "<code>" not in rendered, "Supporting sources should not be wrapped in <code> code blocks"
    assert '<div class="gl-source-item">' in rendered
    print("PASS: test_supporting_sources_rendered_as_html_cards")


if __name__ == "__main__":
    print("Running Streamlit automated AppTests...")
    test_initial_render()
    test_new_question_clears_answer()
    test_supporting_sources_rendered_as_html_cards()
    test_quick_question_pool_timings()
    test_quick_question_maintenance()
    test_custom_question_submit()
    print("\nAll Streamlit AppTests passed successfully!")
