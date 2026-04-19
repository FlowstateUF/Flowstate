import json
import os
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

# Quick checks that the backend and frontend apps are running


BACKEND_URL = os.environ.get("FLOWSTATE_BACKEND_URL", "http://localhost:5001")
FRONTEND_URL = os.environ.get("FLOWSTATE_FRONTEND_URL", "http://localhost:5173")


# Reads a running app url and returns the status, content type, and body
def read_url(url):
    with urlopen(url, timeout=2) as response:
        body = response.read().decode("utf-8")
        return response.status, response.headers.get("Content-Type", ""), body


@unittest.skipUnless(BACKEND_URL, "Set a backend url to run the live app checks.")
class LiveBackendChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.status, cls.content_type, cls.body = read_url(f"{BACKEND_URL}/")
        except (URLError, HTTPError):
            raise unittest.SkipTest("Start the backend app to run the live app checks.")

    # Checks that the running backend responds on its root route
    def test_backend_root(self):
        self.assertEqual(self.status, 200)
        self.assertIn("application/json", self.content_type.lower())
        self.assertEqual(json.loads(self.body), {"message": "Flowstate backend running"})


@unittest.skipUnless(FRONTEND_URL, "Set a frontend url to run the live app checks.")
class LiveFrontendChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.status, cls.content_type, cls.body = read_url(FRONTEND_URL)
        except (URLError, HTTPError):
            raise unittest.SkipTest("Start the frontend app to run the live app checks.")

    # Checks that the running frontend serves the main app shell
    def test_frontend_root(self):
        self.assertEqual(self.status, 200)
        self.assertIn("text/html", self.content_type.lower())
        self.assertIn('<div id="root"></div>', self.body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
