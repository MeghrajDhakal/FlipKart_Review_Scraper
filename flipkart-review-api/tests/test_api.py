import unittest
from app import app


class TestAppAPI(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_root_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("name"), "Flipkart Review API")
        self.assertIn("/v1.0/reviews", data.get("endpoints", {}))

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("status"), "healthy")

    def test_missing_url_parameter(self):
        response = self.client.get("/v1.0/reviews")
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data.get("error"), "Bad Request")
        self.assertIn("Missing required 'url' parameter", data.get("message", ""))


if __name__ == "__main__":
    unittest.main()
