from backend.infrastructure.api.app import app


class TestAppSetup:
    def test_app_exists(self):
        assert app is not None
        assert hasattr(app, "routes")

    def test_404_returns_json_error(self, client):
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404
        assert "detail" in response.json()


class TestSecurityHeaders:
    def test_cors_credentials_header(self, client):
        response = client.get(
            "/api/sentiment",
            headers={"Origin": "http://localhost:4321"},
        )
        assert response.headers["Access-Control-Allow-Credentials"] == "true"

    def test_security_headers_present(self, client):
        response = client.get("/api/sentiment")
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "Strict-Transport-Security" in response.headers
        assert response.headers["Content-Security-Policy"] == "default-src 'self'"

    def test_all_endpoints_return_json(self, client):
        for endpoint in ["/api/sentiment", "/api/comments", "/api/stats"]:
            assert "application/json" in client.get(endpoint).headers["content-type"]
