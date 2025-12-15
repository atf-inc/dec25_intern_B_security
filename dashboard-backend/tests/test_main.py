from fastapi.testclient import TestClient
from unittest.mock import patch
from main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello from dashboard-backend!"}

def test_fetch_emails_no_token():
    # Test missing access token
    response = client.post("/api/v1/emails/fetch", json={"access_token": ""})
    assert response.status_code == 422
    # Pydantic returns a standard validation error structure, not our custom detail
    assert "detail" in response.json()

@patch('main.GmailService')
def test_fetch_emails_success(MockGmailService):
    # Mock the service response
    mock_instance = MockGmailService.return_value
    mock_instance.fetch_recent_emails.return_value = [
        {"id": "1", "subject": "Test", "sender": "me", "status": "clean"}
    ]
    
    response = client.post("/api/v1/emails/fetch", json={"access_token": "fake_token"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["count"] == 1
    assert data["emails"][0]["subject"] == "Test"
