# 🛡️ MailShieldAI - Complete Repository Overview

## 📋 Table of Contents
1. [Project Summary](#project-summary)
2. [Architecture Overview](#architecture-overview)
3. [Technology Stack](#technology-stack)
4. [Directory Structure](#directory-structure)
5. [Core Components](#core-components)
6. [Data Flow](#data-flow)
7. [Database Schema](#database-schema)
8. [API Endpoints](#api-endpoints)
9. [Authentication & Security](#authentication--security)
10. [Deployment](#deployment)
11. [Development Workflow](#development-workflow)

---

## Project Summary

**MailShieldAI** is an AI-powered personal email security dashboard that detects and analyzes phishing threats in real-time. It integrates with Gmail to scan incoming emails, assign risk scores (0-100), and provides actionable insights to protect users from email-based attacks.

### Key Features
- 📧 **Gmail Integration** - Sync and analyze emails via Gmail API
- 🔍 **Real-time Analysis** - Background workers continuously process emails
- 📊 **Risk Scoring** - Categorizes threats as Safe (0-29), Cautious (30-79), or Threat (80-100)
- 🔐 **Google OAuth** - Secure authentication with Google accounts
- 📈 **Modern Dashboard** - Next.js 16 + React 19 interface
- 🚀 **Auto-provisioning** - Users created automatically on first sign-in
- 🤖 **AI Chatbot (Luffy)** - Interactive assistant for email security queries

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER (Browser)                               │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │   Next.js Frontend    │
                    │   (apps/web)          │
                    │   - React 19          │
                    │   - NextAuth.js       │
                    │   - Tailwind CSS      │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │   FastAPI Backend     │
                    │   (apps/api)          │
                    │   - REST API          │
                    │   - Google OAuth      │
                    │   - Gmail Service     │
                    └───────────┬───────────┘
                                │
            ┌───────────────────┼───────────────────┐
            │                   │                   │
    ┌───────▼────────┐  ┌──────▼──────┐  ┌────────▼────────┐
    │  PostgreSQL    │  │   Redis     │  │  Gmail API      │
    │  (Cloud SQL)   │  │   Queue     │  │  (Google)       │
    │  - Users       │  │  - Jobs     │  │  - Messages     │
    │  - Emails      │  │             │  │  - Watch/Sync   │
    └────────────────┘  └─────────────┘  └─────────────────┘
                                │
            ┌───────────────────┴───────────────────┐
            │                                       │
    ┌───────▼────────┐                  ┌──────────▼─────────┐
    │ Ingest Worker  │                  │  Decision Worker   │
    │ (apps/worker/  │                  │  (apps/worker/     │
    │  ingest)       │                  │   decision)        │
    │ - Pub/Sub      │                  │ - Risk Analysis    │
    │ - Extract Data │──────────────────▶│ - Sandbox Check   │
    │ - Forward      │                  │ - Scoring          │
    └────────────────┘                  └────────────────────┘
```

### Component Responsibilities

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Frontend (apps/web)** | User interface, authentication, email display | Next.js 16, React 19, Tailwind |
| **API (apps/api)** | REST endpoints, Gmail sync, user management | FastAPI, SQLModel |
| **Ingest Worker** | Process Gmail Pub/Sub events, extract email data | FastAPI, Gmail API |
| **Decision Worker** | Risk analysis, sandboxing, threat detection | FastAPI, Hybrid Analysis |
| **Database** | Persistent storage for users and emails | PostgreSQL (Cloud SQL) |
| **Queue** | Async job processing | Redis |

---

## Technology Stack

### Backend
- **Python 3.12+** - Core language
- **FastAPI** - REST API framework
- **SQLModel** - ORM with Pydantic integration
- **asyncpg** - Async PostgreSQL driver
- **Google Auth** - OAuth 2.0 and Gmail API
- **Redis** - Job queue management
- **httpx** - Async HTTP client

### Frontend
- **Next.js 16** - React framework with App Router
- **React 19** - UI library
- **NextAuth.js v5** - Authentication
- **Tailwind CSS v4** - Styling
- **Radix UI** - Accessible component primitives
- **Framer Motion** - Animations
- **Recharts** - Data visualization
- **Lucide React** - Icons

### Infrastructure
- **Google Cloud Platform (GCP)**
  - Cloud Run (serverless containers)
  - Cloud SQL (PostgreSQL)
  - Pub/Sub (Gmail notifications)
  - Secret Manager (credentials)
- **Docker** - Containerization
- **uv** - Python package manager
- **pnpm** - Node.js package manager

---

## Directory Structure

```
dec25_intern_B_security/
├── apps/
│   ├── api/                    # FastAPI Backend (Dashboard API)
│   │   ├── main.py            # API entry point, CORS, health check
│   │   ├── routers/           # API route handlers
│   │   │   ├── auth.py        # Authentication endpoints
│   │   │   ├── emails.py      # Email CRUD and sync
│   │   │   └── stats.py       # Dashboard statistics
│   │   └── services/          # Business logic
│   │       ├── auth.py        # JWT verification, user provisioning
│   │       └── gmail.py       # Gmail API integration (32KB!)
│   │
│   ├── web/                   # Next.js Frontend
│   │   ├── app/               # App Router pages
│   │   │   ├── page.tsx       # Landing page
│   │   │   ├── sign-in/       # Sign-in page
│   │   │   ├── emails/        # Email dashboard
│   │   │   └── settings/      # User settings
│   │   ├── components/        # React components
│   │   │   ├── emails-page.tsx      # Main email list
│   │   │   ├── overview-page.tsx    # Dashboard stats
│   │   │   ├── settings-page.tsx    # Settings UI
│   │   │   ├── dashboard-layout.tsx # Layout wrapper
│   │   │   ├── luffy/               # AI Chatbot components
│   │   │   └── ui/                  # Radix UI components
│   │   ├── lib/               # Utilities
│   │   │   └── api.ts         # API client functions
│   │   ├── auth.ts            # NextAuth configuration
│   │   └── middleware.ts      # Route protection
│   │
│   └── worker/                # Background Workers
│       ├── ingest/            # Email Ingest Agent
│       │   └── main.py        # Pub/Sub handler, Gmail extraction
│       ├── decision/          # Decision Agent
│       │   └── main.py        # Risk analysis, sandboxing
│       └── intent/            # Intent Classification (future)
│
├── packages/
│   └── shared/                # Shared Python code
│       ├── models.py          # SQLModel database models
│       ├── constants.py       # Enums (EmailStatus, RiskTier, etc.)
│       ├── database.py        # Database connection
│       └── queue.py           # Redis queue utilities
│
├── scripts/
│   └── seed_db.py            # Database initialization
│
├── .env                       # Environment variables (NOT in git)
├── example.env                # Environment template
├── deploy.sh                  # GCP deployment script
├── pyproject.toml             # Python dependencies (uv)
├── requirements.txt           # Python dependencies (pip)
├── README.md                  # Quick start guide
└── SETUP.md                   # Detailed setup instructions
```

---

## Core Components

### 1. **apps/api/main.py** - API Entry Point
- Initializes FastAPI app
- Configures CORS with strict validation (no wildcards with credentials)
- Registers routers: `/api/auth`, `/api/emails`, `/api/stats`
- Health check endpoint: `GET /health`
- Database initialization on startup
- Global exception handler with CORS headers

### 2. **apps/api/services/gmail.py** - Gmail Integration (937 lines!)
**Key Classes:**
- `StructuredEmail` - Unified email representation
- `EmailAuthenticationStatus` - SPF/DKIM/DMARC results
- `AttachmentMetadata` - Attachment info (no content download)
- `EmailContentExtractor` - Parses MIME structure

**Key Functions:**
- `fetch_gmail_messages()` - Fetches recent emails with full metadata
- `parse_auth_results()` - Extracts SPF/DKIM/DMARC from headers
- `extract_sender_ip()` - Finds originating IP from Received headers
- `extract_urls()` - Extracts URLs for phishing analysis
- `decode_base64url()` - Decodes Gmail's base64url encoding

### 3. **apps/api/services/auth.py** - Authentication
- `verify_google_token()` - Validates Google ID tokens
- `get_current_user()` - FastAPI dependency for protected routes
- Auto-provisions users on first login
- DEV_MODE support for local testing

### 4. **apps/api/routers/emails.py** - Email Endpoints
- `POST /api/emails` - Ingest new email
- `GET /api/emails` - List user's emails (with filters)
- `POST /api/emails/sync` - Sync from Gmail (requires Google token)

### 5. **apps/worker/ingest/main.py** - Ingest Worker (312 lines)
- Receives Gmail Pub/Sub push notifications
- Fetches full message details via Gmail API
- Extracts:
  - Sender, subject, body preview
  - URLs (for phishing detection)
  - Attachment metadata (filename, size, MIME type)
  - Authentication results (SPF/DKIM/DMARC)
- Forwards structured payload to Decision Agent

### 6. **apps/worker/decision/main.py** - Decision Agent (391 lines)
**Risk Gate Logic:**
- Evaluates static indicators (risky extensions, suspicious URLs)
- Decides if sandboxing is needed
- Returns risk score (0-100)

**Sandbox Integration:**
- Submits files/URLs to Hybrid Analysis API
- Polls for results with timeout
- Normalizes verdict to internal format

**Output:**
- Unified decision payload with risk score
- Forwards to final agent (database update)

### 7. **packages/shared/models.py** - Database Models
**User:**
- `id` (UUID), `google_id`, `email`, `name`, `created_at`

**EmailEvent:**
- Identification: `id`, `user_id`, `message_id`, `sender`, `recipient`, `subject`
- Content: `body_preview`, `received_at`
- Security: `spf_status`, `dkim_status`, `dmarc_status`, `sender_ip`, `attachment_info`
- Threat: `threat_category`, `detection_reason`
- Processing: `status`, `risk_score`, `risk_tier`, `analysis_result`
- Timestamps: `created_at`, `updated_at`

### 8. **apps/web/components/emails-page.tsx** - Email Dashboard
- Fetches emails from API
- Displays in sortable table
- Filters by risk tier (Safe/Cautious/Threat)
- Shows threat badges and risk scores
- Sync button to fetch from Gmail

### 9. **apps/web/components/luffy/** - AI Chatbot
- `luffy-chatbot.tsx` - Main chatbot component
- `luffy-message.tsx` - Message rendering (Markdown support)
- `luffy-input.tsx` - User input with suggestions
- `luffy-quick-actions.tsx` - Predefined queries
- Uses Google Generative AI (Gemini)

---

## Data Flow

### Email Sync Flow (User-Initiated)
```
1. User clicks "Sync" in dashboard
   ↓
2. Frontend sends POST /api/emails/sync with Google token
   ↓
3. Backend calls Gmail API (fetch_gmail_messages)
   ↓
4. Extracts metadata (sender, subject, SPF/DKIM/DMARC, etc.)
   ↓
5. Deduplicates by message_id
   ↓
6. Inserts new emails into database (status=PENDING)
   ↓
7. Pushes email IDs to Redis queue
   ↓
8. Returns {status: "synced", new_messages: count}
```

### Gmail Pub/Sub Flow (Real-time)
```
1. Gmail sends Pub/Sub notification (new email)
   ↓
2. Ingest Worker receives POST /pubsub/push
   ↓
3. Decodes Pub/Sub message (email address, history_id)
   ↓
4. Calls Gmail API to fetch changed messages
   ↓
5. Extracts structured data (StructuredEmailPayload)
   ↓
6. Forwards to Decision Agent POST /analyze
   ↓
7. Decision Agent evaluates risk
   ↓
8. If risky, submits to Hybrid Analysis sandbox
   ↓
9. Polls for sandbox results
   ↓
10. Forwards unified decision to Final Agent
    ↓
11. Final Agent updates database (risk_score, threat_category)
```

### Authentication Flow
```
1. User clicks "Sign in with Google"
   ↓
2. NextAuth redirects to Google OAuth
   ↓
3. User grants permissions (Gmail read/modify)
   ↓
4. Google returns access_token, refresh_token, id_token
   ↓
5. NextAuth stores tokens in JWT session
   ↓
6. Frontend sends requests with Authorization: Bearer {id_token}
   ↓
7. Backend verifies token with Google
   ↓
8. Auto-provisions user if first login
   ↓
9. Returns user info
```

---

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    google_id VARCHAR UNIQUE NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    name VARCHAR,
    created_at TIMESTAMP NOT NULL
);
```

### Email Events Table
```sql
CREATE TABLE email_events (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    
    -- Identification
    sender VARCHAR NOT NULL,
    recipient VARCHAR NOT NULL,
    subject VARCHAR NOT NULL,
    message_id VARCHAR UNIQUE,
    body_preview TEXT,
    received_at TIMESTAMP,
    
    -- Security Metadata
    spf_status VARCHAR,
    dkim_status VARCHAR,
    dmarc_status VARCHAR,
    sender_ip VARCHAR,
    attachment_info VARCHAR,
    
    -- Threat Intelligence
    threat_category threat_category_enum,
    detection_reason TEXT,
    
    -- Processing
    status email_status_enum DEFAULT 'PENDING',
    risk_score INTEGER,
    risk_tier risk_tier_enum,
    analysis_result JSON,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

### Enums
```python
EmailStatus = PROCESSING | COMPLETED | FAILED
RiskTier = SAFE | CAUTIOUS | THREAT
ThreatCategory = NONE | PHISHING | MALWARE | SPAM | BEC | SPOOFING | SUSPICIOUS
```

---

## API Endpoints

### Authentication
- `GET /api/me` - Get current user info (requires Bearer token)

### Emails
- `POST /api/emails` - Ingest new email
  - Body: `{sender, recipient, subject, body_preview?}`
  - Returns: Created email with ID
  
- `GET /api/emails` - List user's emails
  - Query: `?status_filter=COMPLETED&limit=100&offset=0`
  - Returns: Array of emails
  
- `POST /api/emails/sync` - Sync from Gmail
  - Header: `X-Google-Token: {access_token}`
  - Returns: `{status: "synced", new_messages: count}`

### Stats
- `GET /api/stats` - Dashboard statistics
  - Returns: `{total_emails, threats_detected, safe_emails, cautious_emails}`

### Health
- `GET /health` - Health check
  - Returns: `{status: "ok"}`

### Workers
**Ingest Worker:**
- `POST /pubsub/push` - Receive Gmail Pub/Sub notifications
  - Body: `{message: {data, messageId, publishTime}, subscription}`
  
**Decision Worker:**
- `POST /analyze` - Analyze email
  - Body: `{message_id, sender, subject, extracted_urls, attachment_metadata}`

---

## Authentication & Security

### Google OAuth Scopes
```javascript
[
  "openid",
  "https://www.googleapis.com/auth/userinfo.email",
  "https://www.googleapis.com/auth/userinfo.profile",
  "https://www.googleapis.com/auth/gmail.readonly",
  "https://www.googleapis.com/auth/gmail.modify"
]
```

### Token Flow
1. **Frontend** - NextAuth stores tokens in encrypted JWT cookie
2. **API Requests** - Frontend sends `Authorization: Bearer {id_token}`
3. **Backend** - Verifies token with Google's public keys
4. **Gmail Sync** - Frontend sends `X-Google-Token: {access_token}`

### Security Features
- **CORS** - Strict origin validation (no wildcards with credentials)
- **Token Verification** - Google ID token validation on every request
- **Auto-provisioning** - Users created on first login (no manual registration)
- **DEV_MODE** - Insecure fallback for local testing (NEVER in production)
- **SSL/TLS** - Required for Cloud SQL connections

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require

# Google OAuth
AUTH_GOOGLE_ID=xxx.apps.googleusercontent.com
AUTH_GOOGLE_SECRET=xxx

# NextAuth
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=xxx

# API
NEXT_PUBLIC_API_URL=http://localhost:8000
CORS_ALLOW_ORIGINS=http://localhost:3000

# Workers
POLL_INTERVAL_SECONDS=5
BATCH_LIMIT=10

# Development
DEV_MODE=false
```

---

## Deployment

### GCP Services
- **Cloud Run** - Serverless containers for API, frontend, workers
- **Cloud SQL** - Managed PostgreSQL database
- **Pub/Sub** - Gmail push notifications
- **Secret Manager** - Secure credential storage
- **Cloud Build** - Automated builds from source

### Deployment Script (`deploy.sh`)
```bash
./deploy.sh
```
Deploys:
1. Dashboard Backend (API) → `mailshield-api`
2. Agent Backend (Worker) → `mailshield-agent`
3. Dashboard Frontend → `mailshield-frontend`

### Manual Steps After Deployment
1. Create Cloud SQL PostgreSQL instance
2. Update environment variables in Cloud Run console
3. Configure CORS origins
4. Add OAuth redirect URIs in Google Cloud Console
5. Set up Gmail Pub/Sub topic and subscription

### Dockerfiles
Each service has a Dockerfile:
- `apps/api/Dockerfile` - FastAPI backend
- `apps/web/Dockerfile` - Next.js frontend (multi-stage build)
- `apps/worker/ingest/Dockerfile` - Ingest worker
- `apps/worker/decision/Dockerfile` - Decision worker

---

## Development Workflow

### Local Setup
```bash
# 1. Clone repository
git clone <repo-url>
cd dec25_intern_B_security

# 2. Copy environment file
cp example.env .env
# Edit .env with your credentials

# 3. Install backend dependencies
cd apps/api
uv sync

# 4. Initialize database
cd ../../scripts
uv run python seed_db.py

# 5. Install frontend dependencies
cd ../apps/web
pnpm install

# 6. Start backend (Terminal 1)
cd ../api
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000

# 7. Start frontend (Terminal 2)
cd ../web
pnpm dev

# 8. (Optional) Start workers
cd ../worker/ingest
uv run python main.py

cd ../decision
uv run python main.py
```

### Testing
- **Backend Tests** - `pytest` (test files in each module)
- **Frontend** - Manual testing in browser
- **DEV_MODE** - Use `dev_anytoken` as Bearer token

### Code Quality
- **Python** - Type hints, docstrings, async/await
- **TypeScript** - Strict mode, proper typing
- **Linting** - ESLint for frontend
- **Formatting** - Consistent style

---

## Key Insights

### Design Decisions
1. **Single User Architecture** - Each user has isolated data (multi-tenant ready)
2. **Async Everything** - FastAPI async, asyncpg, Redis async client
3. **No Attachment Downloads** - Security risk, only metadata stored
4. **Pub/Sub for Real-time** - Gmail watch API + Cloud Pub/Sub
5. **Redis Queue** - Decouples API from workers
6. **Auto-provisioning** - No manual user creation needed

### Performance Optimizations
- **Connection Pooling** - AsyncAdaptedQueuePool for PostgreSQL
- **Thread Pool** - Gmail API calls run in thread pool (blocking I/O)
- **Batch Processing** - Workers process emails in batches
- **Lazy Fetching** - Attachments fetched only when needed for sandbox

### Security Considerations
- **No Wildcard CORS** - Explicit origins only
- **Token Verification** - Every request validates Google token
- **No Client-Side Secrets** - API keys only in backend
- **SSL Required** - Cloud SQL connections use SSL
- **Attachment Isolation** - Never download attachments to API server

### Scalability
- **Stateless Services** - All services can scale horizontally
- **Cloud Run** - Auto-scales based on traffic
- **Redis Queue** - Handles high throughput
- **PostgreSQL** - Cloud SQL can scale vertically

---

## Future Enhancements

1. **Intent Classification Worker** - Categorize email intent (promotional, transactional, etc.)
2. **Email Reply Suggestions** - AI-generated safe responses
3. **Threat Intelligence Feed** - Real-time threat database
4. **User Feedback Loop** - Learn from user corrections
5. **Mobile App** - React Native or Flutter
6. **Multi-language Support** - i18n for global users
7. **Advanced Analytics** - Threat trends, sender reputation
8. **Webhook Integrations** - Slack, Discord notifications

---

## Troubleshooting

### Common Issues
1. **CORS Errors** - Check `CORS_ALLOW_ORIGINS` matches frontend URL exactly
2. **Database Connection Failed** - Verify `DATABASE_URL` and Cloud SQL accessibility
3. **Invalid Token** - Ensure `AUTH_GOOGLE_ID` matches in frontend and backend
4. **Port Already in Use** - Kill process: `lsof -ti:8000 | xargs kill`
5. **Gmail Sync Fails** - Check Google token expiry and scopes

### Logs
- **Backend** - `uvicorn` logs to stdout
- **Frontend** - Browser console + Next.js server logs
- **Workers** - Structured JSON logs (pythonjsonlogger)
- **Cloud Run** - Cloud Logging in GCP Console

---

## Resources

- **README.md** - Quick start guide
- **SETUP.md** - Detailed setup instructions
- **example.env** - Environment variable template
- **API Docs** - http://localhost:8000/docs (Swagger UI)
- **Google Cloud Console** - https://console.cloud.google.com
- **Gmail API Docs** - https://developers.google.com/gmail/api

---

**Last Updated:** 2025-12-22  
**Version:** 0.2.0  
**Maintainer:** MailShieldAI Team
