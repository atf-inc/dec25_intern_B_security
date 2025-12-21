import pytest
import asyncio
from main import evaluate_static_risk, StructuredEmailPayload, AttachmentMetadata, RISKY_EXTENSIONS

# Mock Payload Factory
def create_payload(filename="safe.txt", mime="text/plain", urls=None):
    if urls is None:
        urls = []
    return StructuredEmailPayload(
        message_id="test-123",
        sender="test@example.com",
        subject="Test Subject",
        extracted_urls=urls,
        attachment_metadata=[
            AttachmentMetadata(filename=filename, mime_type=mime, size=1024)
        ] if filename else []
    )

def test_safe_email():
    payload = create_payload(filename="resume.pdf", mime="application/pdf")
    should_sandbox, reason, score = evaluate_static_risk(payload)
    assert should_sandbox is False
    assert score < 50
    print("✅ Safe Email Test Passed")

def test_risky_extension():
    # Test .exe
    payload = create_payload(filename="malware.exe", mime="application/x-msdownload")
    should_sandbox, reason, score = evaluate_static_risk(payload)
    assert should_sandbox is True
    assert "Risky extension" in reason
    assert score >= 70
    print("✅ Risky Extension Test Passed")

def test_archive_attachment():
    # Test .zip
    payload = create_payload(filename="invoice.zip", mime="application/zip")
    should_sandbox, reason, score = evaluate_static_risk(payload)
    assert should_sandbox is True
    assert "Archive" in reason
    print("✅ Archive Test Passed")

def test_many_urls():
    # Test > 3 URLs
    urls = ["http://a.com", "http://b.com", "http://c.com", "http://d.com"]
    payload = create_payload(filename=None, urls=urls)
    should_sandbox, reason, score = evaluate_static_risk(payload)
    assert should_sandbox is True
    assert "Many URLs" in reason
    print("✅ High URL Count Test Passed")

if __name__ == "__main__":
    test_safe_email()
    test_risky_extension()
    test_archive_attachment()
    test_many_urls()
    print("\n🎉 All Decision Agent Logic Tests Passed!")
