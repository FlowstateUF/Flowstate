import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from app.services import llm_service  # type: ignore
except Exception:
    llm_service = None


@unittest.skipIf(
    llm_service is None,
    "Install backend LLM dependencies to run the LLM helper tests.",
)
class LlmHelperTests(unittest.TestCase):
    # Builds a small service instance once for the helper tests.
    def setUp(self):
        self.service = llm_service.LLMService(api_key="test-key")

    # Checks that quiz difficulty splits turn into the expected counts.
    def test_quiz_type_distribution(self):
        self.assertEqual(
            llm_service.build_quiz_type_distribution("easy", 10).splitlines(),
            ["- 7 recall", "- 3 understand"],
        )
        self.assertEqual(
            llm_service.build_quiz_type_distribution("medium", 10).splitlines(),
            ["- 2 recall", "- 5 understand", "- 3 apply"],
        )
        self.assertEqual(
            llm_service.build_quiz_type_distribution("hard", 10).splitlines(),
            ["- 2 understand", "- 4 apply", "- 4 analyze"],
        )

    # Checks that fenced JSON still parses cleanly.
    def test_json_parsing(self):
        data = self.service.parse_json_response(
            """```json
            {"answer": "ok", "grounded": true}
            ```"""
        )

        self.assertEqual(data["answer"], "ok")
        self.assertTrue(data["grounded"])

    # Checks that inline page references are stripped from answer text.
    def test_citation_cleanup(self):
        cleaned = self.service.remove_citations_from_answer(
            "Data structures matter. (Page 12)",
            ["Page 12"],
        )

        self.assertEqual(cleaned, "Data structures matter.")

    # Checks that plain answer text still turns into structured blocks.
    def test_answer_blocks(self):
        blocks = self.service.normalize_answer_blocks(
            None,
            "## Key idea\n- First point\n- Second point",
            ["Page 1", "Page 2"],
        )

        self.assertEqual([block["type"] for block in blocks], ["heading", "bullet", "bullet"])
        self.assertEqual(blocks[1]["citations"], ["Page 1"])
        self.assertEqual(blocks[2]["citations"], ["Page 2"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
