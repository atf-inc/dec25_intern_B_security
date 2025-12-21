# MailShieldAI - Data Flow & Processing Pipeline

## 📧 Complete Email Processing Flow

This document details the end-to-end data flow through MailShieldAI, from email arrival to threat detection.

---

## 🔄 Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          GMAIL INBOX                                 │
│                     (User's Gmail Account)                           │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ (Two paths: Manual Sync OR Real-time Watch)
                             │
        ┌────────────────────┴────────────────────┐
        │                                         │
        │ PATH 1: Manual Sync                     │ PATH 2: Real-time Watch
        │ (User clicks "Sync")                    │ (Gmail Pub/Sub)
        │                                         │
        ▼                                         ▼
┌───────────────────┐                    ┌───────────────────┐
│  Frontend Button  │                    │  Gmail Pub/Sub    │
│  "Sync Emails"    │                    │  Notification     │
└─────────┬─────────┘                    └─────────┬─────────┘
          │                                        │
          │ POST /api/emails/sync                  │ POST /pubsub/push
          │ X-Google-Token: {access_token}         │ {message: {data, id}}
          │                                        │
          ▼                                        ▼
┌─────────────────────────────────────┐  ┌─────────────────────────────┐
│   Dashboard Backend (apps/api)      │  │  Ingest Worker              │
│   routers/emails.py::sync_emails()  │  │  (apps/worker/ingest)       │
└─────────┬───────────────────────────┘  └─────────┬───────────────────┘
          │                                        │
          │ 1. Call Gmail API                      │ 1. Decode Pub/Sub msg
          │    fetch_gmail_messages()              │ 2. Extract history_id
          │                                        │ 3. Call Gmail API
          │ 2. Extract metadata:                   │    users().history().list()
          │    - Sender, subject, body             │
          │    - SPF/DKIM/DMARC                    │ 4. Fetch full message
          │    - Sender IP                         │    users().messages().get()
          │    - Attachments                       │
          │                                        │ 5. Extract content:
          │ 3. Deduplicate by message_id           │    - URLs
          │                                        │    - Attachments metadata
          │ 4. Insert into database                │    - Authentication headers
          │    status = PENDING                    │
          │                                        │ 6. Build StructuredEmailPayload
          │ 5. Push to Redis queue                 │
          │    EMAIL_PROCESSING_QUEUE              │ 7. Forward to Decision Agent
          │                                        │    POST /analyze
          ▼                                        │
┌─────────────────────────────────────┐            │
│   PostgreSQL Database                │            │
│   - email_events table               │◀───────────┘
│   - status: PENDING                  │
└─────────┬───────────────────────────┘
          │
          │ (Both paths converge here)
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Decision Agent (apps/worker/decision)            │
│                     POST /analyze                                    │
└─────────┬───────────────────────────────────────────────────────────┘
          │
          │ 1. Receive StructuredEmailPayload
          │    {message_id, sender, subject, urls, attachments}
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     RISK GATE (Static Analysis)                      │
│                     evaluate_static_risk()                           │
└─────────┬───────────────────────────────────────────────────────────┘
          │
          │ Check for:
          │ ✓ Risky file extensions (.exe, .scr, .vbs, .js, .bat, .iso)
          │ ✓ Suspicious URLs (bit.ly, tinyurl, etc.)
          │ ✓ Multiple attachments
          │
          │ Calculate static_risk_score (0-100)
          │
          ├─────────────────┬─────────────────┐
          │                 │                 │
    LOW RISK          MEDIUM RISK       HIGH RISK
    (score < 30)      (30-70)          (score > 70)
          │                 │                 │
          │                 │                 │
          ▼                 ▼                 ▼
    Skip Sandbox    Optional Sandbox   ALWAYS Sandbox
          │                 │                 │
          │                 └─────────┬───────┘
          │                           │
          │                           ▼
          │              ┌────────────────────────────────┐
          │              │  Hybrid Analysis Sandbox       │
          │              │  hybrid_analysis_scan()        │
          │              └────────────┬───────────────────┘
          │                           │
          │                           │ 1. Fetch attachment from Gmail
          │                           │    fetch_attachment_from_gmail()
          │                           │
          │                           │ 2. Submit to Hybrid Analysis
          │                           │    POST /submit/file OR /submit/url
          │                           │
          │                           │ 3. Poll for results (max 5 min)
          │                           │    GET /report/{job_id}
          │                           │
          │                           │ 4. Normalize verdict
          │                           │    {verdict, score, family, confidence}
          │                           │
          │                           ▼
          │              ┌────────────────────────────────┐
          │              │  SandboxResult                 │
          │              │  - malicious / suspicious /    │
          │              │    clean / unknown             │
          │              │  - score: 0-100                │
          │              └────────────┬───────────────────┘
          │                           │
          └───────────────────────────┘
                          │
                          ▼
          ┌────────────────────────────────────────────┐
          │  Unified Decision Payload                  │
          │  {                                         │
          │    message_id,                             │
          │    static_risk_score,                      │
          │    sandboxed: true/false,                  │
          │    sandbox_result: {...},                  │
          │    decision_metadata: {provider, reason}   │
          │  }                                         │
          └────────────┬───────────────────────────────┘
                       │
                       │ Forward to Final Agent
                       │ POST /finalize
                       │
                       ▼
          ┌────────────────────────────────────────────┐
          │  Final Agent (Future)                      │
          │  OR Direct Database Update                 │
          └────────────┬───────────────────────────────┘
                       │
                       │ Update email_events:
                       │ - status = COMPLETED
                       │ - risk_score = calculated score
                       │ - risk_tier = SAFE/CAUTIOUS/THREAT
                       │ - threat_category = PHISHING/MALWARE/etc.
                       │ - detection_reason = explanation
                       │ - analysis_result = full JSON
                       │
                       ▼
          ┌────────────────────────────────────────────┐
          │  PostgreSQL Database                       │
          │  email_events table UPDATED                │
          └────────────┬───────────────────────────────┘
                       │
                       │ Frontend polls or WebSocket updates
                       │
                       ▼
          ┌────────────────────────────────────────────┐
          │  Dashboard UI (apps/web)                   │
          │  - Email list refreshes                    │
          │  - Risk badges update                      │
          │  - Stats counters increment                │
          └────────────────────────────────────────────┘
```

---

## 📊 Detailed Component Interactions

### 1. Gmail API Integration

**Location:** `apps/api/services/gmail.py`

**Key Functions:**
- `fetch_gmail_messages(access_token, max_results=20)` - Fetches recent emails
- `parse_auth_results(auth_results)` - Extracts SPF/DKIM/DMARC
- `extract_sender_ip(received_headers)` - Finds originating IP
- `extract_urls(text)` - Extracts URLs for analysis

**Data Extracted:**
```python
{
  "message_id": "abc123",
  "sender": "attacker@evil.com",
  "recipient": "victim@example.com",
  "subject": "Urgent: Reset your password",
  "body_preview": "Click here to reset...",
  "received_at": "2025-12-22T00:00:00Z",
  "spf_status": "FAIL",
  "dkim_status": "FAIL",
  "dmarc_status": "FAIL",
  "sender_ip": "123.45.67.89",
  "attachment_info": "invoice.exe, document.pdf",
  "status": "PENDING"
}
```

---

### 2. Ingest Worker (Pub/Sub Handler)

**Location:** `apps/worker/ingest/main.py`

**Trigger:** Gmail Pub/Sub push notification

**Input:**
```json
{
  "message": {
    "data": "base64_encoded_data",
    "messageId": "123456",
    "publishTime": "2025-12-22T00:00:00Z"
  },
  "subscription": "projects/xxx/subscriptions/gmail-watch"
}
```

**Decoded Data:**
```json
{
  "emailAddress": "user@example.com",
  "historyId": "987654"
}
```

**Process:**
1. Decode Base64 Pub/Sub message
2. Extract `emailAddress` and `historyId`
3. Call Gmail API `users().history().list(startHistoryId=historyId)`
4. For each changed message, fetch full details
5. Extract content using `extract_message_content()`
6. Build `StructuredEmailPayload`
7. Forward to Decision Agent

**Output:**
```python
StructuredEmailPayload(
  message_id="abc123",
  sender="attacker@evil.com",
  subject="Urgent: Reset your password",
  extracted_urls=["http://evil.com/phish", "http://bit.ly/xyz"],
  attachment_metadata=[
    AttachmentMetadata(
      filename="invoice.exe",
      mime_type="application/x-msdownload",
      size=1024000,
      attachment_id="att_123"
    )
  ]
)
```

---

### 3. Decision Agent (Risk Analysis)

**Location:** `apps/worker/decision/main.py`

**Input:** `StructuredEmailPayload`

#### Phase 1: Static Risk Evaluation

**Function:** `evaluate_static_risk(payload)`

**Checks:**
- Risky file extensions: `.exe`, `.scr`, `.vbs`, `.js`, `.bat`, `.iso`, `.dll`, `.ps1`
- Suspicious URL shorteners: `bit.ly`, `tinyurl.com`, `goo.gl`, `t.co`
- Multiple attachments (> 3)
- Unusual sender domains

**Scoring:**
```python
risk_score = 0

# Risky extension: +40 points
if any(ext in filename for ext in RISKY_EXTENSIONS):
    risk_score += 40

# Suspicious URL: +30 points
if any(shortener in url for shortener in URL_SHORTENERS):
    risk_score += 30

# Multiple attachments: +20 points
if len(attachments) > 3:
    risk_score += 20

# Cap at 100
risk_score = min(risk_score, 100)
```

**Decision:**
- `risk_score >= 70` → **ALWAYS sandbox**
- `30 <= risk_score < 70` → **OPTIONAL sandbox** (based on config)
- `risk_score < 30` → **SKIP sandbox**

#### Phase 2: Sandbox Analysis (if needed)

**Function:** `hybrid_analysis_scan(payload)`

**Steps:**
1. **Fetch Attachment** (lazy loading)
   ```python
   attachment_data = fetch_attachment_from_gmail(message_id, attachment_id)
   ```

2. **Submit to Hybrid Analysis**
   ```python
   job_id = submit_to_hybrid_analysis(
       file_content=attachment_data,
       filename="invoice.exe"
   )
   ```

3. **Poll for Results** (max 5 minutes)
   ```python
   report = poll_ha_report(job_id, timeout=300)
   ```

4. **Normalize Verdict**
   ```python
   SandboxResult(
       verdict="malicious",  # or suspicious/clean/unknown
       score=95,
       family="Trojan.Generic",
       confidence=0.98
   )
   ```

#### Phase 3: Unified Decision

**Output:**
```python
UnifiedDecisionPayload(
  message_id="abc123",
  static_risk_score=70,
  sandboxed=True,
  sandbox_result=SandboxResult(
    verdict="malicious",
    score=95,
    family="Trojan.Generic",
    confidence=0.98
  ),
  decision_metadata=DecisionMetadata(
    provider="hybrid_analysis",
    timed_out=False,
    reason="Risky file extension + malicious sandbox verdict"
  )
)
```

---

### 4. Database Update (Final Agent)

**Location:** Currently in Decision Agent, will be separate service

**Process:**
1. Receive `UnifiedDecisionPayload`
2. Calculate final risk score:
   ```python
   final_score = max(static_risk_score, sandbox_result.score if sandboxed else 0)
   ```
3. Determine risk tier:
   ```python
   if final_score < 30:
       risk_tier = RiskTier.SAFE
   elif final_score < 80:
       risk_tier = RiskTier.CAUTIOUS
   else:
       risk_tier = RiskTier.THREAT
   ```
4. Assign threat category:
   ```python
   if sandbox_result.verdict == "malicious":
       threat_category = ThreatCategory.MALWARE
   elif "phish" in detection_reason.lower():
       threat_category = ThreatCategory.PHISHING
   else:
       threat_category = ThreatCategory.SUSPICIOUS
   ```
5. Update database:
   ```sql
   UPDATE email_events
   SET status = 'COMPLETED',
       risk_score = 95,
       risk_tier = 'THREAT',
       threat_category = 'MALWARE',
       detection_reason = 'Risky file extension + malicious sandbox verdict',
       analysis_result = '{"sandbox": {...}, "static": {...}}',
       updated_at = NOW()
   WHERE message_id = 'abc123';
   ```

---

### 5. Frontend Display

**Location:** `apps/web/components/emails-page.tsx`

**Process:**
1. Poll API every 5 seconds: `GET /api/emails`
2. Receive updated email list
3. Render with risk badges:
   ```tsx
   {email.risk_tier === 'THREAT' && (
     <Badge className="bg-red-500">
       🔴 THREAT ({email.risk_score})
     </Badge>
   )}
   ```
4. Show threat details in modal:
   ```tsx
   <Dialog>
     <DialogContent>
       <h3>Threat Analysis</h3>
       <p>Category: {email.threat_category}</p>
       <p>Reason: {email.detection_reason}</p>
       <pre>{JSON.stringify(email.analysis_result, null, 2)}</pre>
     </DialogContent>
   </Dialog>
   ```

---

## 🔄 State Transitions

### Email Status Flow

```
PENDING → PROCESSING → COMPLETED
                    ↘ FAILED
```

**PENDING:**
- Email just inserted into database
- Waiting for worker to pick up

**PROCESSING:**
- Worker is analyzing email
- Risk gate evaluation in progress
- Sandbox scan running (if needed)

**COMPLETED:**
- Analysis finished successfully
- Risk score assigned
- Ready for display

**FAILED:**
- Error during analysis
- Sandbox timeout
- Gmail API error

---

## 📈 Performance Metrics

### Typical Processing Times

| Stage | Duration | Notes |
|-------|----------|-------|
| Gmail API Fetch | 500ms - 2s | Depends on message size |
| Static Risk Eval | < 100ms | Pure computation |
| Sandbox Submit | 1-2s | HTTP request to HA |
| Sandbox Analysis | 30s - 5min | Depends on file complexity |
| Database Update | < 100ms | Single UPDATE query |
| **Total (no sandbox)** | **< 3s** | Fast path |
| **Total (with sandbox)** | **30s - 5min** | Slow path |

### Optimization Strategies

1. **Lazy Attachment Fetching** - Only download if sandboxing needed
2. **Async Processing** - Workers run in background
3. **Redis Queue** - Decouples API from workers
4. **Connection Pooling** - Reuse database connections
5. **Batch Processing** - Workers process multiple emails at once

---

## 🔐 Security Considerations

### Data Privacy
- **No Attachment Storage** - Attachments never stored in database
- **Metadata Only** - Only filenames, sizes, MIME types stored
- **Encrypted Tokens** - Google tokens encrypted in NextAuth JWT
- **SSL/TLS** - All connections use encryption

### Threat Detection
- **Multi-layered** - Static analysis + dynamic sandbox
- **Defense in Depth** - SPF/DKIM/DMARC + content analysis
- **Zero Trust** - All emails analyzed, even from known senders

### Error Handling
- **Graceful Degradation** - If sandbox fails, use static score
- **Timeout Protection** - Sandbox polls have 5-minute timeout
- **Retry Logic** - Failed jobs can be retried
- **Logging** - All errors logged with context

---

## 🎯 Future Enhancements

### Planned Features
1. **Intent Classification** - Categorize email purpose (promotional, transactional, etc.)
2. **Sender Reputation** - Track sender history and patterns
3. **Machine Learning** - Train models on user feedback
4. **Real-time Alerts** - Push notifications for high-risk emails
5. **Email Reply Suggestions** - AI-generated safe responses
6. **Threat Intelligence Feed** - External threat database integration

### Architecture Improvements
1. **Separate Final Agent** - Dedicated service for database updates
2. **WebSocket Updates** - Real-time frontend updates (no polling)
3. **Caching Layer** - Redis cache for frequently accessed data
4. **Rate Limiting** - Protect against API abuse
5. **Multi-region Deployment** - Global availability

---

**Last Updated:** 2025-12-22  
**Version:** 0.2.0
