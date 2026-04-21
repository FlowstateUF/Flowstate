import io
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from flask import Flask  # type: ignore
    from app import routes  # type: ignore
except Exception:
    Flask = None
    routes = None


@unittest.skipIf(
    Flask is None or routes is None,
    "Install backend app dependencies to run the textbook route tests.",
)
class TextbookRouteTests(unittest.TestCase):
    # Builds a small Flask app with auth bypassed for textbook workflow tests
    def setUp(self):
        self.jwt_patch = patch.object(
            routes,
            "jwt_required",
            lambda *args, **kwargs: (lambda fn: fn),
        )
        self.identity_patch = patch.object(routes, "get_jwt_identity", lambda: "test-user")
        self.jwt_patch.start()
        self.identity_patch.start()
        self.addCleanup(self.jwt_patch.stop)
        self.addCleanup(self.identity_patch.stop)

        app = Flask(__name__)
        routes.register_routes(app)
        self.client = app.test_client()

    # Builds a small fake Supabase response for owned textbook checks
    def make_owned_textbook(self):
        return SimpleNamespace(data=[{"id": "book-1"}])

    # Posts a file the same way the upload form sends it
    def upload_file(self, file_bytes, filename="book.pdf"):
        return self.client.post(
            "/api/upload",
            data={"file": (io.BytesIO(file_bytes), filename)},
            content_type="multipart/form-data",
        )

    # Checks that oversized uploads return the friendly limit message
    def test_upload_rejects_oversized_pdf(self):
        with patch.object(routes, "get_textbook_upload_limit_bytes", return_value=10):
            response = self.upload_file(b"hello world", filename="big-book.pdf")

        payload = response.get_json()

        self.assertEqual(response.status_code, 413)
        self.assertEqual(payload["limit_mb"], 50)
        self.assertIn("uploads are capped at 50 MB", payload["error"])

    # Checks that uploading the same textbook again returns the existing-book response
    def test_upload_returns_existing_textbook(self):
        existing = {
            "id": "book-1",
            "title": "WorldHistory.pdf",
            "status": "ready",
        }

        with patch.object(routes, "check_textbook_exists", return_value=existing), patch.object(
            routes,
            "upload_textbook_to_supabase",
        ) as upload_mock:
            response = self.upload_file(b"pdf bytes")

        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "exists")
        self.assertEqual(payload["textbook_id"], "book-1")
        self.assertEqual(payload["processing_status"], "ready")
        upload_mock.assert_not_called()

    # Checks that a valid upload stores TOC data and queues background processing
    def test_upload_starts_processing_for_new_textbook(self):
        textbook = {
            "id": "book-1",
            "title": "WorldHistory.pdf",
            "storage_path": "textbooks/test-user/book-1.pdf",
        }
        toc = [{"title": "1 Prehistory", "start_page": 10, "end_page": 29}]

        with patch.object(routes, "check_textbook_exists", return_value=None), patch.object(
            routes,
            "upload_textbook_to_supabase",
            return_value=textbook,
        ), patch.object(
            routes,
            "extract_toc",
            return_value=(toc, 417),
        ), patch.object(
            routes,
            "store_toc",
        ) as store_toc_mock, patch.object(
            routes.process_textbook,
            "delay",
        ) as delay_mock:
            response = self.upload_file(b"pdf bytes")

        payload = response.get_json()

        self.assertEqual(response.status_code, 202)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["textbook_id"], "book-1")
        store_toc_mock.assert_called_once_with("book-1", toc, 417)
        delay_mock.assert_called_once_with("test-user", "book-1", b"pdf bytes")

    # Checks that the status route returns the serialized textbook card
    def test_status_route_returns_textbook_card(self):
        card = {
            "id": "book-1",
            "title": "World History",
            "status": "ready",
        }

        with patch.object(routes, "get_textbook", return_value=self.make_owned_textbook()), patch.object(
            routes,
            "get_textbook_info",
            return_value={"id": "book-1", "title": "WorldHistory.pdf", "status": "ready"},
        ), patch.object(
            routes,
            "serialize_textbook_card",
            return_value=card,
        ):
            response = self.client.get("/api/textbooks/book-1/status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), card)

    # Checks that a ready textbook returns its saved chapter list
    def test_chapters_route_returns_saved_toc(self):
        chapters = [
            {"id": "chapter-1", "title": "1 Prehistory", "start_page": 10, "end_page": 29},
            {"id": "chapter-2", "title": "2 Early Civilizations", "start_page": 30, "end_page": 52},
        ]

        with patch.object(routes, "get_textbook", return_value=self.make_owned_textbook()), patch.object(
            routes,
            "get_toc",
            return_value=chapters,
        ):
            response = self.client.get("/api/textbooks/book-1/chapters")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"chapters": chapters})

    # Checks that deleting a textbook returns success after cleanup runs
    def test_delete_route_returns_success(self):
        with patch.object(routes, "get_textbook", return_value=self.make_owned_textbook()), patch.object(
            routes,
            "delete_textbook_chunks",
        ) as delete_chunks_mock, patch.object(
            routes,
            "delete_textbook_for_user",
            return_value={"id": "book-1"},
        ) as delete_book_mock:
            response = self.client.delete("/api/textbooks/book-1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {
                "status": "success",
                "message": "Textbook deleted successfully",
            },
        )
        delete_chunks_mock.assert_called_once_with("test-user", "book-1")
        delete_book_mock.assert_called_once_with("test-user", "book-1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
