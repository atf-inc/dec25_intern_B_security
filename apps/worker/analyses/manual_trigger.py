import httpx
import asyncio
import uuid
import json

# Configuration
DECISION_AGENT_URL = "http://localhost:9000/analyze"

# Test Case: Phishing URL (Triggers Hybrid Analysis URL Scan)
# We use a URL that looks suspicious to trigger the Risk Gate, 
# but ultimately we want to test the HA submission.
# Note: "http://malware.com" is just a string; the Risk Gate looks for count/patterns.
# To force a sandbox, we can use a known risky extension in metadata OR many URLs.
# Let's use a "Risky Extension" trigger to force the "should_sandbox" flag,
# BUT provide a URL to scan so we don't need to fetch a file from Gmail.
# Wait - if we trigger via Extension, it tries to fetch the file.
# If we trigger via URL count, it tries to submit the URL.
# Let's trigger via URL count (>3 URLs).

PAYLOAD_URL_TRIGGER = {
    "message_id": f"manual-test-{uuid.uuid4()}",
    "sender": "attacker@example.com",
    "subject": "Urgent: Check these links",
    "extracted_urls": [
        "http://example.com", 
        "http://google.com",
        "http://wikipedia.org",
        "http://github.com"
    ],
    "attachment_metadata": []
}

async def run_test():
    print(f"--- Sending Manual Test Payload to {DECISION_AGENT_URL} ---")
    print(f"Message ID: {PAYLOAD_URL_TRIGGER['message_id']}")
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(DECISION_AGENT_URL, json=PAYLOAD_URL_TRIGGER)
            print(f"Response Status: {resp.status_code}")
            print(f"Response Body: {resp.json()}")
            
            if resp.status_code == 202:
                print("\n✅ Request Accepted! Check your terminal logs for:")
                print("1. 'Risk Gate Result: sandboxed=True'")
                print("2. 'Submitting URL ... to Hybrid Analysis'")
                print("3. 'Forwarding decision to Final Agent'")
            else:
                print("❌ Request Failed.")
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            print("Make sure the Decision Agent is running on port 9000.")

if __name__ == "__main__":
    asyncio.run(run_test())
