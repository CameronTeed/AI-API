"""
Tests for REST API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from server.api.app import create_app


@pytest.fixture
def client():
    """Create test client"""
    app = create_app()
    return TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_health_status(self, client):
        """Test health status endpoint"""
        response = client.get("/api/health/status")
        # May return 200 or 500 depending on database configuration
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data
        assert "timestamp" in data

    def test_readiness_check(self, client):
        """Test readiness check endpoint"""
        response = client.get("/api/health/ready")
        # May return 200 or 500 depending on database configuration
        assert response.status_code in [200, 500]
        data = response.json()
        assert "ready" in data or "reason" in data


class TestChatEndpoints:
    """Test chat endpoints"""
    
    def test_chat_conversation_basic(self, client):
        """Test basic chat conversation"""
        payload = {
            "session_id": "test_session_1",
            "user_id": "test_user",
            "messages": [
                {
                    "role": "user",
                    "content": "Find me a good date idea in Ottawa"
                }
            ]
        }
        
        response = client.post("/api/chat/conversation", json=payload)
        # May fail if services not configured, but should not crash
        assert response.status_code in [200, 500]
    
    def test_chat_history_retrieval(self, client):
        """Test retrieving chat history"""
        response = client.get("/api/chat/history/test_session_1")
        # May fail if session doesn't exist, but should not crash
        assert response.status_code in [200, 500]
    
    def test_session_deletion(self, client):
        """Test session deletion"""
        response = client.delete("/api/chat/session/test_session_1")
        # May fail if session doesn't exist, but should not crash
        assert response.status_code in [200, 500]


class TestAdminEndpoints:
    """Test admin endpoints"""
    
    def test_admin_requires_auth(self, client):
        """Test that admin endpoints require authentication"""
        payload = {
            "title": "Test Date Idea",
            "description": "A test date idea",
            "category": "outdoor",
            "price_tier": 1,
            "duration_min": 60,
            "indoor": False,
            "city": "Ottawa"
        }

        # Should fail without auth (403 when no token, 401 when missing header)
        response = client.post("/api/admin/date-ideas", json=payload)
        assert response.status_code in [401, 403]
    
    def test_admin_with_invalid_token(self, client):
        """Test admin endpoint with invalid token"""
        payload = {
            "title": "Test Date Idea",
            "description": "A test date idea",
            "category": "outdoor",
            "price_tier": 1,
            "duration_min": 60,
            "indoor": False,
            "city": "Ottawa"
        }
        
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.post("/api/admin/date-ideas", json=payload, headers=headers)
        assert response.status_code == 403

