# 🛡️ MailShieldAI 

An AI-powered email security platform that detects and analyzes phishing threats in real-time. MailShieldAI scans incoming emails, assigns risk scores, and provides actionable insights to protect organizations from email-based attacks.

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js%2016-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React%2019-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)

---

## ✨ Features

- **📧 Gmail Integration** — Sync and analyze emails directly from Gmail accounts
- **🔍 Real-time Analysis** — Background worker continuously processes incoming emails
- **📊 Risk Scoring** — Assigns risk scores (0-100) and categorizes threats as Safe, Cautious, or Threat
- **🏢 Multi-tenant** — Organizations with isolated data and API keys
- **🔐 Google OAuth** — Secure authentication with Google accounts
- **👥 Role-based Access** — Platform Admin, Admin, and Member roles
- **📈 Dashboard UI** — Modern Next.js interface for threat monitoring

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
                        │     PostgreSQL       │
                        │     / SQLite         │
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
- **uv** (Python): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **pnpm** (Node): `npm install -g pnpm`

### 1. Configure

From the root of the cloned repository, run:

```bash
cd dec25_intern_B_security
cp example.env dashboard-backend/.env
```

Edit `dashboard-backend/.env` with your credentials:
```properties
DATABASE_URL=sqlite+aiosqlite:///./app.db
AUTH_GOOGLE_ID=your-google-client-id
CORS_ALLOW_ORIGINS=http://localhost:3000
```

### 2. Start Backend

```bash
cd dashboard-backend
uv sync
uv run python seed_db.py    # Initialize database
uv run fastapi dev main.py  # Starts on http://127.0.0.1:8000
```

### 3. Start Frontend

```bash
cd dashboard
echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000" > .env.local
pnpm install
pnpm dev  # Starts on http://localhost:3000
```

### 4. Add Users

```bash
cd dashboard-backend
# Get your Google ID from backend logs after sign-in attempt
./.venv/bin/python add_user.py "YOUR_GOOGLE_ID" "your.email@gmail.com" --admin
```

> 📖 For detailed setup instructions, see [SETUP.md](./SETUP.md)

---

## 📡 API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/health` | Health check | None |
| `POST` | `/api/emails` | Ingest new email | API Key / Bearer |
| `GET` | `/api/emails` | List analyzed emails | Bearer |
| `POST` | `/api/emails/sync` | Sync from Gmail | Bearer + Google Token |
| `POST` | `/api/organizations` | Create organization | Platform Admin |
| `GET` | `/api/organizations` | List organizations | Platform Admin |
| `POST` | `/api/users` | Create user | Admin |
| `GET` | `/api/users` | List users | Admin |
| `PATCH` | `/api/users/{id}/role` | Update user role | Admin |

**API Documentation:** http://127.0.0.1:8000/docs

---

## 🔒 Security

- **API Keys** — Securely hashed with SHA-256, only prefix shown after creation
- **Google OAuth** — Production-grade authentication with token verification
- **CORS** — Strict origin validation (wildcards blocked in production)
- **Role-based Access** — Fine-grained permissions per endpoint

### User Roles

| Role | Permissions |
|------|-------------|
| `platform_admin` | Full access across all organizations |
| `admin` | Manage users and emails within their organization |
| `member` | View emails within their organization |

---

## 📊 Risk Classification

| Score | Tier | Description |
|-------|------|-------------|
| 0-29 | 🟢 **SAFE** | Low risk, no suspicious indicators |
| 30-79 | 🟡 **CAUTIOUS** | Moderate risk, review recommended |
| 80-100 | 🔴 **THREAT** | High risk, likely phishing attempt |

---

## 🛠️ Development

### Run Tests

```bash
# Backend
cd dashboard-backend
uv run pytest

# Agent
cd agent-backend
uv run pytest
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | Database connection string | ✅ |
| `AUTH_GOOGLE_ID` | Google OAuth Client ID | ✅ (prod) |
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
│   ├── seed_db.py          # Database seeding script
│   └── add_user.py         # User management CLI
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
