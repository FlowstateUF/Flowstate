import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from app.services.supabase_service import (  # type: ignore
        build_confidence_gap_point,
        classify_confidence_gap,
        confidence_label_to_percent,
        get_reported_question_count,
        should_skip_quiz_attempt_analytics,
    )
except Exception:
    build_confidence_gap_point = None
    classify_confidence_gap = None
    confidence_label_to_percent = None
    get_reported_question_count = None
    should_skip_quiz_attempt_analytics = None


@unittest.skipIf(
    build_confidence_gap_point is None,
    "Install backend app dependencies to run the quiz logic tests.",
)
class QuizLogicTests(unittest.TestCase):
    # Checks that the confidence labels map to the expected percentages.
    def test_confidence_labels(self):
        self.assertEqual(confidence_label_to_percent("low"), 0.25)
        self.assertEqual(confidence_label_to_percent("medium"), 0.70)
        self.assertEqual(confidence_label_to_percent("high"), 1.00)
        self.assertIsNone(confidence_label_to_percent("sure"))

    # Checks that confidence gaps classify into the right buckets.
    def test_gap_labels(self):
        self.assertEqual(classify_confidence_gap(0.65, 0.60), "accurate")
        self.assertEqual(classify_confidence_gap(0.95, 0.40), "overconfidence")
        self.assertEqual(classify_confidence_gap(0.30, 0.80), "underconfidence")

    # Checks that one confidence point is shaped into the stats payload we expect.
    def test_gap_point(self):
        point = build_confidence_gap_point(
            kind="quiz",
            title="Chapter 1 Quiz",
            attempt_id="attempt-1",
            quiz_id="quiz-1",
            chapter_id="chapter-1",
            chapter_title="Chapter 1",
            completed_at="2026-04-19T12:00:00Z",
            question_points=[(1.0, 1.0), (0.7, 0.0), (0.25, 1.0)],
        )

        self.assertIsNotNone(point)
        self.assertEqual(point["kind"], "quiz")
        self.assertEqual(point["title"], "Chapter 1 Quiz")
        self.assertEqual(point["confidence_percent"], 65)
        self.assertEqual(point["actual_percent"], 67)
        self.assertEqual(point["category"], "accurate")

    # Checks that reported-question counts are read cleanly from saved answers.
    def test_reported_count(self):
        self.assertEqual(get_reported_question_count({"__reported_count": 3}), 3)
        self.assertEqual(get_reported_question_count({"__reported_count": "2"}), 2)
        self.assertEqual(get_reported_question_count({"0": {"answer": "A"}}), 0)

    # Checks that heavily skipped quizzes are ignored by mastery/confidence analytics.
    def test_skip_rule(self):
        self.assertFalse(should_skip_quiz_attempt_analytics({"answers": {"__reported_count": 2}}))
        self.assertTrue(should_skip_quiz_attempt_analytics({"answers": {"__reported_count": 3}}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
