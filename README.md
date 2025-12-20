# 🛡️ MailShieldAI 

An AI-powered personal email security dashboard that detects and analyzes phishing threats in real-time. MailShieldAI scans your incoming emails, assigns risk scores, and provides actionable insights to protect you from email-based attacks.

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js%2016-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React%2019-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)

---

## ✨ Features

- **📧 Gmail Integration** — Sync and analyze emails directly from your Gmail account
- **🔍 Real-time Analysis** — Background worker continuously processes incoming emails
- **📊 Risk Scoring** — Assigns risk scores (0-100) and categorizes threats as Safe, Cautious, or Threat
- **🔐 Google OAuth** — Secure authentication with your Google account
- **📈 Dashboard UI** — Modern Next.js interface for personal threat monitoring
- **🚀 Auto-provisioning** — Just sign in with Google and start using immediately

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│                 │     │                      │     │                 │
│   Dashboard     │────▶│   Dashboard Backend  │◀────│  Agent Backend  │
│   (Next.js)     │     │   (FastAPI)          │     │  (Worker)       │
│                 │     │                      │     │                 │
└─────────────────┘     └──────────┬───────────┘     └─────────────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │  PostgreSQL (GCP)    │
                        └──────────────────────┘
```

| Component | Description | Tech Stack |
|-----------|-------------|------------|
| `dashboard/` | Web UI for viewing emails and threat analysis | Next.js 16, React 19, Tailwind CSS, Radix UI |
| `dashboard-backend/` | REST API for authentication, email ingestion, and data access | FastAPI, SQLModel, Google OAuth |
| `agent-backend/` | Background worker for processing emails and risk analysis | Python async worker, SQLModel |

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+**
- **Node.js 18+**
- **PostgreSQL** (GCP Cloud SQL recommended)
- **uv** (Python): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **pnpm** (Node): `npm install -g pnpm`

### 1. Configure

From the root of the cloned repository, run:

```bash
cp example.env dashboard-backend/.env
cp example.env dashboard/.env.local
```

Edit `dashboard-backend/.env` with your credentials:
```properties
DATABASE_URL=postgresql://user:password@host:5432/mailshieldai
AUTH_GOOGLE_ID=your-google-client-id
AUTH_GOOGLE_SECRET=your-google-client-secret
CORS_ALLOW_ORIGINS=http://localhost:3000
```

Edit `dashboard/.env.local`:
```properties
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
AUTH_GOOGLE_ID=your-google-client-id
AUTH_GOOGLE_SECRET=your-google-client-secret
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-random-secret
```

### 2. Start Backend

```bash
cd dashboard-backend
uv sync
uv run python seed_db.py    # Initialize database (creates tables)
uv run fastapi dev main.py  # Starts on http://127.0.0.1:8000
```

### 3. Start Frontend

```bash
cd dashboard
pnpm install
pnpm dev  # Starts on http://localhost:3000
```

### 4. Sign In

Simply visit http://localhost:3000 and sign in with your Google account. Your user account is automatically created on first login!

> 📖 For detailed setup instructions, see [SETUP.md](./SETUP.md)

---

## 📡 API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/health` | Health check | None |
| `GET` | `/api/me` | Get current user info | Bearer |
| `POST` | `/api/emails` | Ingest new email | Bearer |
| `GET` | `/api/emails` | List analyzed emails | Bearer |
| `POST` | `/api/emails/sync` | Sync from Gmail | Bearer + Google Token |
| `GET` | `/api/stats` | Get email statistics | Bearer |

**API Documentation:** http://127.0.0.1:8000/docs

---

## 🔒 Security

- **Google OAuth** — Production-grade authentication with token verification
- **CORS** — Strict origin validation (wildcards blocked in production)
- **Auto-provisioning** — Users created automatically on first Google sign-in
- **PostgreSQL** — Production-ready database with connection pooling

---

## 📊 Risk Classification

| Score | Tier | Description |
|-------|------|-------------|
| 0-29 | 🟢 **SAFE** | Low risk, no suspicious indicators |
| 30-79 | 🟡 **CAUTIOUS** | Moderate risk, review recommended |
| 80-100 | 🔴 **THREAT** | High risk, likely phishing attempt |

---

## 🛠️ Development

### Dev Mode

For local development without Google OAuth:

```bash
# In dashboard-backend/.env
DEV_MODE=true
```

Then use `dev_anytoken` as your bearer token for API requests.

### Run Worker

```bash
cd agent-backend
uv sync
uv run python -m worker
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | ✅ |
| `AUTH_GOOGLE_ID` | Google OAuth Client ID | ✅ (prod) |
| `AUTH_GOOGLE_SECRET` | Google OAuth Client Secret | ✅ (prod) |
| `CORS_ALLOW_ORIGINS` | Comma-separated allowed origins | ✅ |
| `DEV_MODE` | Enable dev mode (bypasses strict auth) | ❌ |
| `POLL_INTERVAL_SECONDS` | Worker poll interval | ❌ (default: 5) |
| `BATCH_LIMIT` | Worker batch size | ❌ (default: 10) |

---

## 📁 Project Structure

```
.
├── dashboard/              # Next.js frontend
│   ├── app/                # App router pages
│   ├── components/         # Reusable UI components
│   └── lib/                # Utilities
├── dashboard-backend/      # FastAPI REST API
│   ├── main.py             # API routes and auth
│   ├── models.py           # SQLModel database models
│   ├── database.py         # Database connection
│   └── seed_db.py          # Database seeding script
├── agent-backend/          # Background worker
│   ├── worker.py           # Email processing loop
│   ├── models.py           # Shared models
│   └── database.py         # Database connection
├── example.env             # Environment template
└── SETUP.md                # Detailed setup guide
```

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
