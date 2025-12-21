# Action Agent Documentation

> The "Enforcer" - Third and final agent in the MailShieldAI security pipeline

## Overview

The Action Agent consumes security verdicts from the Decision Agent, applies Gmail labels to classify emails, and uses Gemini AI as a fallback for "unknown" verdicts.

```
┌─────────────┐     ┌────────────────┐     ┌──────────────┐
│ Ingest Agent│────▶│ Decision Agent │────▶│ Action Agent │
│  (Parser)   │     │   (Analyzer)   │     │  (Enforcer)  │
└─────────────┘     └────────────────┘     └──────────────┘
                                                   │
                                           ┌───────┴───────┐
                                           ▼               ▼
                                      Gmail API      Gemini API
                                    (Apply Labels)  (URL Analysis)
```

---

## File Structure

```
apps/worker/action/
├── main.py              # FastAPI app with /execute endpoint
├── gmail_labels.py      # Gmail label management utilities
├── ai_fallback.py       # Gemini AI URL analysis
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container deployment
└── test_action_logic.py # Unit tests
```

---

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/execute` | POST | Async processing (returns 202 immediately) |
| `/execute-sync` | POST | Sync processing (returns full result) |
| `/health` | GET | Health check with Gemini status |
| `/stats` | GET | Processing statistics |

---

## Verdict-to-Label Mapping

| Verdict | Gmail Label | Color | Action |
|---------|-------------|-------|--------|
| `malicious` | MailShield/MALICIOUS | 🔴 Red | Move to Spam |
| `suspicious` | MailShield/CAUTIOUS | 🟠 Orange | Keep in Inbox |
| `clean` | MailShield/SAFE | 🟢 Green | Keep in Inbox |
| `unknown` | → Gemini Fallback | — | AI Analysis |

---

## Input Payload

```json
{
  "message_id": "gmail-msg-id-123",
  "static_risk_score": 85,
  "sandboxed": true,
  "sandbox_result": {
    "verdict": "malicious",
    "score": 90,
    "family": "TrojanDownloader",
    "confidence": 0.95
  },
  "decision_metadata": {
    "provider": "hybrid-analysis",
    "timed_out": false,
    "reason": "Risky extension .exe"
  },
  "extracted_urls": ["http://evil.com/payload"]
}
```

---

## Output Response

```json
{
  "message_id": "gmail-msg-id-123",
  "original_verdict": "malicious",
  "final_verdict": "malicious",
  "label_applied": "MailShield/MALICIOUS",
  "moved_to_spam": true,
  "ai_analysis_used": false,
  "ai_reasoning": null
}
```

---

## Gemini AI Fallback

When the Decision Agent returns `verdict: "unknown"`, the Action Agent triggers Gemini AI to analyze the extracted URLs.

### Analysis Patterns

Gemini looks for:
- **Typosquatting**: paypa1.com, amaz0n.com
- **Suspicious TLDs**: .xyz, .top, .click
- **Deceptive subdomains**: login-paypal.evil.com
- **URL shorteners**: bit.ly, tinyurl
- **IP-based URLs**: Direct IP addresses

### Response Format

```json
{
  "verdict": "malicious",
  "reason": "Typosquatting detected: paypa1.com mimics paypal.com"
}
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 9001 | Server port |
| `GEMINI_API_KEY` | — | Required for AI fallback |
| `MOVE_MALICIOUS_TO_SPAM` | true | Auto-move threats to spam |

---

## Running Locally

```bash
cd apps/worker/action
pip install -r requirements.txt
export GEMINI_API_KEY=your-key  # Optional
python main.py
# Server starts on http://localhost:9001
```

### Test Commands

```bash
# Health check
curl http://localhost:9001/health

# Test malicious verdict
curl -X POST http://localhost:9001/execute-sync \
  -H "Content-Type: application/json" \
  -d '{"message_id":"test-1","static_risk_score":85,"sandboxed":true,"sandbox_result":{"verdict":"malicious","score":90},"decision_metadata":{"provider":"mock","timed_out":false}}'

# Check stats
curl http://localhost:9001/stats
```

---

## Architecture Features

### Concurrency Control
- **Gmail Semaphore**: 5 concurrent API calls
- **Gemini Semaphore**: 2 concurrent AI calls

### Idempotency
- In-memory set tracks processed message IDs
- Duplicate requests are skipped

### Label Caching
- Labels cached after first creation
- Handles 409 Conflict (race conditions)

### Error Handling
- Gmail errors logged but don't crash the agent
- Gemini failures default to "suspicious" verdict

---

## Gmail API Scope

The Action Agent requires `gmail.modify` scope (not just `gmail.readonly`):

```python
scopes=['https://www.googleapis.com/auth/gmail.modify']
```

Update your Google Cloud OAuth consent screen to include this scope.

---

## Production Deployment

### Docker

```bash
cd apps/worker/action
docker build -t action-agent .
docker run -p 9001:8080 -e GEMINI_API_KEY=xxx action-agent
```

### Cloud Run

```bash
gcloud run deploy action-agent \
  --source apps/worker/action \
  --set-env-vars GEMINI_API_KEY=xxx
```

---

## Integration with Decision Agent

Update the Decision Agent's environment:

```bash
FINAL_AGENT_URL=http://action-agent:9001/execute
```

The Decision Agent calls this URL after completing sandbox analysis.
