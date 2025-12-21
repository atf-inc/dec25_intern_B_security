import json
import logging
from main import extract_message_content

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_extraction():
    # Load sample JSON
    with open('gmail_message_full.json', 'r') as f:
        message_detail = json.load(f)

    print("\n--- Testing Extraction Logic ---")
    payload = extract_message_content(message_detail)

    print(f"Message ID: {payload.message_id}")
    print(f"Sender: {payload.sender}")
    print(f"Subject: {payload.subject}")
    print(f"URLs: {payload.extracted_urls}")
    print(f"Attachments: {payload.attachment_metadata}")

    # Assertions
    assert payload.message_id == "msg-12345"
    assert "Bad Actor <bad@example.com>" in payload.sender
    assert payload.subject == "Urgent: Unpaid Invoice"
    
    # Check URLs (Base64 decoded content)
    # plain text: "Please click here: http://malware.com/download"
    # html: "<html><body><a href="https://fishing-site.com">Click Here</a></body></html>"
    expected_urls = {"http://malware.com/download", "https://fishing-site.com"}
    extracted_set = set(payload.extracted_urls)
    assert expected_urls.issubset(extracted_set), f"Missing URLs. Expected {expected_urls}, got {extracted_set}"

    # Check Attachments
    assert len(payload.attachment_metadata) == 1
    att = payload.attachment_metadata[0]
    assert att.filename == "invoice.pdf"
    assert att.mime_type == "application/pdf"
    assert att.size == 10240

    print("\n✅ Verification PASSED")

if __name__ == "__main__":
    test_extraction()
