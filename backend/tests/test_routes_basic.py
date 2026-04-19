import sys
import unittest
from pathlib import Path
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
    "Install backend app dependencies to run the route tests.",
)
class BasicRouteTests(unittest.TestCase):
    # Builds a small Flask app with auth bypassed for validation-only route tests.
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

    # Checks that the health route returns the backend-running message.
    def test_root_route(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"message": "Flowstate backend running"})

    # Checks that quiz generation rejects a request without a textbook id.
    def test_quiz_route_requires_textbook_id(self):
        response = self.client.post("/api/generate/quiz", json={})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "textbook_id required")

    # Checks that quiz generation rejects unsupported difficulty values before service calls.
    def test_quiz_route_rejects_bad_difficulty(self):
        response = self.client.post(
            "/api/generate/quiz",
            json={
                "textbook_id": "book-1",
                "chapter_id": "chapter-1",
                "chapter_title": "Chapter 1",
                "difficulty": "extreme",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("difficulty must be easy, medium, hard, or 1-3", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
