# 🛡️ MailShieldAI

An AI-powered email security platform that detects and analyzes phishing threats in real-time using a multi-agent architecture. MailShieldAI processes incoming emails through a pipeline of specialized workers, assigns risk scores, and automatically applies Gmail labels to protect users from email-based attacks.

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js%2016-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React%2019-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)

---

## ✨ Features

- **🔍 Multi-Agent Security Pipeline** — Intent analysis, sandbox analysis, and automated action execution
- **📧 Gmail Integration** — Real-time email sync via Pub/Sub and Gmail API
- **🧠 AI-Powered Analysis** — LangGraph agents for intent classification and threat detection
- **📊 Risk Scoring** — Intelligent categorization: Safe, Cautious, or Threat
- **🏷️ Automated Gmail Labels** — Auto-labeling based on security analysis results
- **🔐 Google OAuth** — Secure authentication with Google accounts
- **📈 Modern Dashboard** — Next.js 16 UI with real-time email monitoring
- **⚡ Redis Streams** — Event-driven architecture with consumer groups

---

## 🏗️ Architecture

### System Overview

```
┌───────────────┐      ┌─────────────┐      ┌──────────────────────┐
│   Gmail API   │─────▶│  Pub/Sub    │─────▶│  Ingest Worker       │
│  (Push Mode)  │      │  (Events)   │      │  (Port 8001)         │
└───────────────┘      └─────────────┘      └──────────┬───────────┘
                                                        │
         ┌──────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│                          Redis Streams                             │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌─────────────┐ │
│  │  Control   │  │  Intent    │  │  Analysis  │  │  Final      │ │
│  │  Queue     │  │  Done      │  │  Done      │  │  Report     │ │
│  └────────────┘  └────────────┘  └────────────┘  └─────────────┘ │
└────────────────────────────────────────────────────────────────────┘
         │               │               │                │
         ▼               ▼               ▼                ▼
┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐
│   Intent    │  │   Sandbox    │  │ Aggregator  │  │    Action    │
│   Worker    │  │   Analysis   │  │   Worker    │  │    Worker    │
│ (Port 8002) │  │ (Port 8004)  │  │ (Port 8005) │  │ (Port 8003)  │
└─────────────┘  └──────────────┘  └─────────────┘  └──────────────┘
         │               │               │                │
         └───────────────┴───────────────┴────────────────┘
                                │
                ┌───────────────┴────────────────┐
                ▼                                ▼
        ┌───────────────┐              ┌─────────────────┐
        │  PostgreSQL   │              │   Gmail API     │
        │  (Database)   │              │  (Auto-label)   │
        └───────────────┘              └─────────────────┘
                ▲
                │
        ┌───────┴────────┐
        ▼                ▼
┌──────────────┐   ┌─────────────┐
│  Dashboard   │   │     API     │
│  (Next.js)   │──▶│  (FastAPI)  │
│ (Port 3000)  │   │ (Port 8000) │
└──────────────┘   └─────────────┘
```

### Worker Pipeline Flow

1. **Ingest Worker** (`apps/worker/ingest`) - Receives Gmail Pub/Sub events
2. **API** (`apps/api`) - Orchestrates email processing, publishes to Redis Streams
3. **Intent Worker** (`apps/worker/intent`) - Analyzes email intent using LLM
4. **Sandbox Worker** (`apps/worker/analyses`) - Performs URL/attachment analysis
5. **Aggregator Worker** (`apps/worker/aggregator`) - Combines results, updates database
6. **Action Worker** (`apps/worker/action`) - Applies Gmail labels based on verdict

### Component Details

| Component | Port | Description | Tech Stack |
|-----------|------|-------------|------------|
| **API** | 8000 | REST API, orchestration, auth | FastAPI, SQLModel, Google OAuth |
| **Web Dashboard** | 3000 | Email security dashboard UI | Next.js 16, React 19, Tailwind v4 |
| **Ingest Worker** | 8001 | Pub/Sub message handler | FastAPI, httpx |
| **Intent Worker** | 8002 | LLM-based intent classification | LangGraph, Gemini AI |
| **Action Worker** | 8003 | Gmail label automation | Gmail API, Python |
| **Sandbox Worker** | 8004 | URL/attachment threat analysis | LangChain, OpenAI |
| **Aggregator Worker** | 8005 | Result aggregation & DB updates | Redis, asyncpg |

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+**
- **Node.js 18+** and **pnpm**
- **PostgreSQL** database
- **Redis** server
- **Docker** (optional, for local Redis/PostgreSQL)

### Installation

#### 1. Install Python Package Manager

```bash
# Install uv (fast Python package installer)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### 2. Install Node Package Manager

```bash
# Install pnpm globally
npm install -g pnpm
```

#### 3. Clone and Setup

```bash
git clone <repository-url>
cd MailShieldAI

# Copy environment variables
cp example.env .env

# Install Python dependencies
uv sync

# Install Node dependencies
npm run install:all
```

#### 4. Setup Services

**Start PostgreSQL** (local):
```bash
docker run --name mailshield-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=mailshieldai \
  -p 5432:5432 -d postgres:16
```

**Start Redis** (local):
```bash
docker run --name mailshield-redis \
  -p 6379:6379 -d redis:7-alpine
```

#### 5. Configure Environment

Edit `.env` with your credentials:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/mailshieldai

# Redis
REDIS_URL=redis://localhost:6379

# Google OAuth (get from Google Cloud Console)
AUTH_GOOGLE_ID=your-client-id.apps.googleusercontent.com
AUTH_GOOGLE_SECRET=your-client-secret

# API Config
CORS_ALLOW_ORIGINS=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000

# NextAuth
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=generate-with-openssl-rand-base64-32

# AI APIs
GEMINI_API_KEY=your-gemini-api-key
```

#### 6. Initialize Database

```bash
npm run db:init
```

---

## 🎯 Running the Application

### Option 1: Run Everything (Recommended)

```bash
npm run dev:all
```

This starts all services in parallel:
- **API** (Port 8000)
- **Web Dashboard** (Port 3000)
- **Ingest Worker** (Port 8001)
- **Intent Worker** (Port 8002)
- **Action Worker** (Port 8003)
- **Sandbox Worker** (Port 8004)
- **Aggregator Worker** (Port 8005)

### Option 2: Run Individually

**API + Dashboard Only:**
```bash
npm run dev
```

**Individual Workers:**
```bash
# In separate terminals
npm run dev:api          # API Server
npm run dev:web          # Next.js Dashboard
npm run dev:ingest       # Ingest Worker
npm run dev:intent       # Intent Analysis Worker
npm run dev:action       # Action Worker
npm run dev:analyses     # Sandbox Analysis Worker
npm run dev:aggregator   # Aggregator Worker
```

### Accessing the Application

- **Dashboard**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Checks**: 
  - API: http://localhost:8000/health
  - Workers: http://localhost:800{1-5}/health

---

## 📡 API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/health` | Health check | None |
| `GET` | `/api/auth/me` | Get current user info | Bearer |
| `POST` | `/api/emails/ingest` | Manual email ingestion | Bearer |
| `GET` | `/api/emails` | List analyzed emails | Bearer |
| `POST` | `/api/emails/sync/background` | Pub/Sub webhook | Internal |
| `GET` | `/api/stats` | Email statistics | Bearer |

**Full API Documentation**: http://localhost:8000/docs

---

## 🔧 Development

### Project Scripts

```bash
# Development
npm run dev              # API + Web
npm run dev:all          # All services
npm run dev:api          # API only
npm run dev:web          # Dashboard only

# Database
npm run db:init          # Initialize/seed database
npm run db:seed          # Re-seed database

# Build & Production
npm run build:web        # Build Next.js
npm run start:web        # Start production server

# Utilities
npm run install:all      # Install all dependencies
npm run lint:web         # Lint frontend code
```

### Development Mode

Enable `DEV_MODE` in `.env` to bypass strict auth:

```bash
DEV_MODE=true
```

Then use `dev_anytoken` as your bearer token for API requests.

---

## 🗂️ Project Structure

```
MailShieldAI/
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── main.py            # App entry, CORS, routes
│   │   ├── routers/           # API route handlers
│   │   │   ├── auth.py        # Google OAuth
│   │   │   ├── emails.py      # Email ingestion & listing
│   │   │   └── stats.py       # Statistics
│   │   └── services/          # Business logic
│   │       ├── auth.py        # JWT verification
│   │       └── gcp_secrets.py # Secret management
│   │
│   ├── web/                   # Next.js dashboard
│   │   ├── app/               # App router pages
│   │   ├── components/        # React components
│   │   ├── lib/               # Utilities
│   │   └── auth.ts            # NextAuth config
│   │
│   └── worker/                # Worker services
│       ├── ingest/            # Pub/Sub handler
│       │   └── main.py
│       ├── intent/            # Intent classifier
│       │   ├── main.py
│       │   ├── prompts.py     # LLM prompts
│       │   └── taxonomy.py    # Intent categories
│       ├── action/            # Gmail labeler
│       │   ├── main.py
│       │   └── gmail_labels.py
│       ├── analyses/          # Sandbox worker
│       │   └── main.py
│       └── aggregator/        # Result aggregator
│           └── main.py
│
├── packages/
│   └── shared/                # Shared Python modules
│       ├── database.py        # DB connection
│       ├── logger.py          # Logging config
│       ├── models.py          # SQLModel schemas
│       ├── queue.py           # Redis connection
│       ├── types.py           # Enums & types
│       └── constants.py       # Shared constants
│
├── scripts/
│   └── seed_db.py            # Database seeding
│
├── .env                       # Environment config
├── package.json               # NPM scripts
├── pyproject.toml            # Python dependencies
├── requirements.txt          # Pip dependencies
└── uv.lock                   # Locked dependencies
```

---

## 🔒 Security Features

- **Multi-Layer Analysis**: Intent + Sandbox + Aggregation
- **Intent Categories**: Phishing, Malware, BEC Fraud, Social Engineering, Reconnaissance
- **Google OAuth**: Production-grade authentication
- **CORS Protection**: Strict origin validation
- **PII Anonymization**: Masked email logging
- **Auto Gmail Labels**: `MailShield/MALICIOUS`, `MailShield/CAUTIOUS`, `MailShield/SAFE`

---

## 📊 Risk Classification

| Score | Tier | Label | Description |
|-------|------|-------|-------------|
| 0-29 | 🟢 **SAFE** | `MailShield/SAFE` | Low risk, legitimate email |
| 30-79 | 🟡 **CAUTIOUS** | `MailShield/CAUTIOUS` | Moderate risk, review recommended |
| 80-100 | 🔴 **THREAT** | `MailShield/MALICIOUS` | High risk, likely attack |

---

## 🌐 Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host/db` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `AUTH_GOOGLE_ID` | Google OAuth Client ID | `*.apps.googleusercontent.com` |
| `AUTH_GOOGLE_SECRET` | Google OAuth Client Secret | `GOCSPX-***` |
| `CORS_ALLOW_ORIGINS` | Allowed origins (comma-separated) | `http://localhost:3000` |
| `GEMINI_API_KEY` | Google Gemini API key | `AIza***` |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `DEV_MODE` | `false` | Enable dev mode |
| `POLL_INTERVAL_SECONDS` | `5` | Worker poll interval |
| `MOVE_MALICIOUS_TO_SPAM` | `true` | Auto-move malicious to spam |
| `API_BASE_URL` | `http://api:8000` | Internal API URL |

---

## 📚 Additional Documentation

- [SETUP.md](./SETUP.md) - Detailed setup guide
- [DATA_FLOW.md](./DATA_FLOW.md) - Data flow documentation
- [REPOSITORY_OVERVIEW.md](./REPOSITORY_OVERVIEW.md) - Codebase overview

---

## 📜 License

This project is for internal use.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
