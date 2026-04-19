import sys
import unittest
from pathlib import Path


SERVICES_DIR = Path(__file__).resolve().parents[1] / "app" / "services"
TEST_TEXTBOOKS_DIR = Path(__file__).resolve().parents[1] / "test_textbooks"
if str(SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICES_DIR))

import textbook_helpers # type: ignore

try:
    import textbook_service # type: ignore
except Exception:
    textbook_service = None


class ChapterParsingTests(unittest.TestCase):
    # Uses a fake TOC so the parsing tests stay fast and predictable
    def setUp(self):
        self.chapters = [
            {"title": "1 Prehistory", "start_page": 10, "end_page": 29},
            {"title": "2 Early Civilizations", "start_page": 30, "end_page": 52},
        ]

    # Checks that chapter words still map to the right number
    def test_word_numbers(self):
        self.assertEqual(textbook_helpers.chapter_word_to_number("twenty-one"), 21)
        self.assertEqual(textbook_helpers.chapter_word_to_number("thirty five"), 35)

    # Checks that roman numerals convert cleanly for chapter matching
    def test_roman_numbers(self):
        self.assertEqual(textbook_helpers.roman_to_number("iv"), 4)
        self.assertEqual(textbook_helpers.roman_to_number("xii"), 12)

    # Checks that we can pull a chapter number from a saved TOC title
    def test_title_numbers(self):
        self.assertEqual(
            textbook_helpers.chapter_identifier_from_title("Chapter One: Prehistory"),
            "1",
        )
        self.assertEqual(
            textbook_helpers.chapter_identifier_from_title("2 Early Civilizations"),
            "2",
        )

    # Checks that common chapter typos still match the intended chapter
    def test_typo_match(self):
        match = textbook_helpers.find_referenced_chapter("go over hcpater one", self.chapters)
        self.assertIsNotNone(match)
        self.assertEqual(match["title"], "1 Prehistory")

    # Checks that title matching still works even when formatting differs.
    def test_title_match(self):
        match = textbook_helpers.find_chapter_by_title("prehistory", self.chapters)
        self.assertIsNotNone(match)
        self.assertEqual(match["title"], "1 Prehistory")


class PageLabelTests(unittest.TestCase):
    # Uses a tiny fake TOC so the page-label tests stay fast and predictable
    def setUp(self):
        self.chapters = [
            {"title": "1 Prehistory", "start_page": 10, "end_page": 29},
            {"title": "2 Early Civilizations", "start_page": 30, "end_page": 52},
        ]

    # Checks that front matter and content pages map to the shown book labels
    def test_display_labels(self):
        self.assertEqual(textbook_helpers.physical_page_to_display_label(1, self.chapters), "i")
        self.assertEqual(textbook_helpers.physical_page_to_display_label(10, self.chapters), "1")
        self.assertEqual(textbook_helpers.physical_page_to_display_label(12, self.chapters), "3")

    # Checks that shown page numbers map back to the stored PDF page.
    def test_physical_pages(self):
        self.assertEqual(textbook_helpers.display_page_to_physical_page(1, self.chapters), 10)
        self.assertEqual(textbook_helpers.display_page_to_physical_page(3, self.chapters), 12)

    # Checks that display citations use the book's shown page labels.
    def test_display_citation(self):
        self.assertEqual(
            textbook_helpers.build_display_citation(1, 1, self.chapters),
            "Page i",
        )
        self.assertEqual(
            textbook_helpers.build_display_citation(10, 29, self.chapters),
            "Pages 1-20",
        )

    # Checks that page label normalization updates the rows we send to llm
    def test_apply_labels(self):
        rows = [
            {"page_number": 1, "page_end": 1, "citation": "Page 1"},
            {"page_number": 12, "page_end": 13, "citation": "Pages 12-13"},
        ]

        labeled_rows = textbook_helpers.apply_display_page_labels(rows, self.chapters)

        self.assertEqual(labeled_rows[0]["display_page_label"], "i")
        self.assertEqual(labeled_rows[0]["citation"], "Page i")
        self.assertEqual(labeled_rows[1]["display_page_label"], "3")
        self.assertEqual(labeled_rows[1]["citation"], "Pages 3-4")

    # Checks that chapter-specific retrieval drops roman numeral front matter rows.
    def test_filter_front_matter(self):
        rows = [
            {"display_page_label": "i", "citation": "Page i"},
            {"display_page_label": "3", "citation": "Page 3"},
        ]

        filtered_rows = textbook_helpers.filter_rows_for_chapter_content(rows)

        self.assertEqual(len(filtered_rows), 1)
        self.assertEqual(filtered_rows[0]["display_page_label"], "3")

    # Checks that the quick chapter range reply uses display-page citations.
    def test_range_response(self):
        answer, citations = textbook_helpers.build_chapter_range_response(
            self.chapters[0],
            self.chapters,
        )

        self.assertIn("spans this page range", answer)
        self.assertEqual(citations, ["Pages 1-20"])


@unittest.skipIf(
    textbook_service is None,
    "Install backend PDF parsing dependencies to run the real textbook TOC tests.",
)
class TocHelperTests(unittest.TestCase):
    # Checks that main chapter detection ignores subsection numbering.
    def test_main_titles(self):
        self.assertTrue(textbook_service.isMainChapterTitle("Chapter One: Prehistory"))
        self.assertTrue(textbook_service.isMainChapterTitle("2 Early Civilizations"))
        self.assertFalse(textbook_service.isMainChapterTitle("1.1 Early Humans"))

    # Checks that front matter and end matter are treated as skippable TOC entries.
    def test_skippable_titles(self):
        self.assertTrue(textbook_service.isSkippableTocTitle("Contents"))
        self.assertTrue(textbook_service.isSkippableTocTitle("Index"))
        self.assertFalse(textbook_service.isSkippableTocTitle("1 Prehistory"))

    # Checks that top-level numbered chapters are preferred over subsection entries.
    def test_main_entries(self):
        toc = [
            [1, "Contents", 1],
            [1, "1 Prehistory", 10],
            [2, "1.1 Humans", 12],
            [1, "2 Early Civilizations", 30],
            [2, "2.1 Mesopotamia", 32],
        ]

        entries = textbook_service.selectMainChapterEntries(toc)

        self.assertEqual(
            [entry[1] for entry in entries],
            ["1 Prehistory", "2 Early Civilizations"],
        )

    # Checks that chapter end pages are built from the next chapter start.
    def test_chapter_ranges(self):
        entries = [
            (1, "1 Prehistory", 10),
            (1, "2 Early Civilizations", 30),
            (1, "3 Classical Age", 53),
        ]

        ranges = textbook_service.buildChapterRanges(entries, total_pages=70)

        self.assertEqual(ranges[0]["end_page"], 29)
        self.assertEqual(ranges[1]["end_page"], 52)
        self.assertEqual(ranges[2]["end_page"], 70)

    # Checks that page labels normalize cleanly for PDF page-label lookups.
    def test_page_labels(self):
        self.assertEqual(textbook_service.normalizePageLabel(" xii "), "xii")
        self.assertEqual(textbook_service.normalizePageLabel("Page 10"), "page10")


@unittest.skipIf(
    textbook_service is None,
    "Install backend PDF parsing dependencies to run the real textbook TOC tests.",
)
class PdfTocTests(unittest.TestCase):
    # Checks that World History TOC extraction gets the first chapter range we expect.
    def test_world_history_toc(self):
        pdf_bytes = (TEST_TEXTBOOKS_DIR / "WorldHistory.pdf").read_bytes()

        toc, total_pages = textbook_service.extract_toc(pdf_bytes)

        self.assertGreater(total_pages, 0)
        self.assertGreater(len(toc), 5)
        self.assertEqual(textbook_helpers.chapter_identifier_from_title(toc[0]["title"]), "1")
        self.assertIn("prehistory", toc[0]["title"].lower())
        self.assertEqual(
            textbook_helpers.physical_page_to_display_label(toc[0]["start_page"], toc),
            "1",
        )
        self.assertEqual(
            textbook_helpers.physical_page_to_display_label(toc[0]["end_page"], toc),
            "20",
        )

    # Checks that the data structures book extracts numbered chapter entries from its TOC.
    def test_data_structures_toc(self):
        pdf_bytes = (TEST_TEXTBOOKS_DIR / "A&D.pdf").read_bytes()

        toc, total_pages = textbook_service.extract_toc(pdf_bytes)
        titles = [chapter["title"] for chapter in toc]

        self.assertGreater(total_pages, 0)
        self.assertTrue(any("Why Data Structures Matter" in title for title in titles))
        self.assertFalse(any("contents" in title.lower() for title in titles))


if __name__ == "__main__":
    unittest.main(verbosity=2)
