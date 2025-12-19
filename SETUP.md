# MailShieldAI - Local Development Setup

This guide helps team members set up and run MailShieldAI locally. The project consists of a **FastAPI backend**, a **Next.js frontend**, and a **background worker** — all connected to a shared **GCP Cloud SQL (PostgreSQL)** database.

---

## 🚀 Quick Start (For Collaborators)

If the project is already configured and you have access to the shared `.env` file:

### 1. Clone & Install Dependencies

```bash
# Clone the repository
git clone <repo-url>
cd dec25_intern_B_security

# Install backend dependencies
cd dashboard-backend && uv sync && cd ..

# Install frontend dependencies
cd dashboard && pnpm install && cd ..

# Install worker dependencies (optional)
cd agent-backend && uv sync && cd ..
```

### 2. Get the Environment File

Ask your teammate for the `.env` file and place it in the **project root**:

```
dec25_intern_B_security/
├── .env              <-- Place the shared .env here
├── dashboard/
├── dashboard-backend/
└── agent-backend/
```

> ⚠️ **Never commit `.env` to git!** It contains secrets.

### 3. Run the Application

Open **two terminals**:

**Terminal 1 - Backend:**
```bash
cd dashboard-backend && uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd dashboard && pnpm dev
```

### 4. Access the App

- **Frontend:** http://localhost:3000
- **Backend API:** http://127.0.0.1:8000
- **API Docs:** http://127.0.0.1:8000/docs

---

## 📋 Prerequisites

| Tool | Version | Installation |
|------|---------|--------------|
| Python | 3.12+ | [python.org](https://python.org) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| pnpm | latest | `npm install -g pnpm` |
| GCP CLI | latest | [cloud.google.com/sdk](https://cloud.google.com/sdk/docs/install) |

---

## 🗄️ Database (GCP Cloud SQL)

We use a **shared PostgreSQL database** on GCP Cloud SQL. Both team members connect to the same database.

### Connecting to Cloud SQL

The `DATABASE_URL` in `.env` should already be configured. If you need to connect directly:

```bash
# Option 1: Direct connection (if Cloud SQL has public IP)
# DATABASE_URL is already in .env

# Option 2: Using Cloud SQL Proxy (for private instances)
cloud-sql-proxy <INSTANCE_CONNECTION_NAME> &
# Then use: postgresql://user:pass@127.0.0.1:5432/dbname
```

### Initialize Database Tables (First Time Only)

One team member runs this once to create tables:

```bash
cd dashboard-backend
uv run python seed_db.py
```

---

## ⚙️ Full Setup (First Time Configuration)

### 1. Backend Setup (`dashboard-backend/`)

```bash
cd dashboard-backend

# Create .env from template (or copy from teammate)
cp ../example.env .env

# Install dependencies
uv sync

# Initialize database (first time only)
uv run python seed_db.py

# Start the server
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Required `.env` variables for backend:**
```properties
# Database (GCP Cloud SQL)
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE

# Google OAuth
AUTH_GOOGLE_ID=your-client-id.apps.googleusercontent.com
AUTH_GOOGLE_SECRET=your-client-secret

# CORS (must match frontend URL)
CORS_ALLOW_ORIGINS=http://localhost:3000

# Dev mode (set to false for production)
DEV_MODE=false
```

### 2. Frontend Setup (`dashboard/`)

```bash
cd dashboard

# Install dependencies
pnpm install

# Start the dev server
pnpm dev
```

**Required `.env.local` or root `.env` variables for frontend:**
```properties
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000

# Google OAuth (same as backend)
AUTH_GOOGLE_ID=your-client-id.apps.googleusercontent.com
AUTH_GOOGLE_SECRET=your-client-secret

# NextAuth.js
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=generate-with-openssl-rand-base64-32
```

### 3. Worker Setup (`agent-backend/`) - Optional

The background worker processes pending emails and assigns risk scores.

```bash
cd agent-backend

# Install dependencies
uv sync

# Run the worker
uv run python -m worker
```

---

## 👥 Team Collaboration Notes

### Sharing Environment Variables

1. **Share `.env` securely** (e.g., via 1Password, encrypted message, NOT via git)
2. Both teammates use the **same** `DATABASE_URL` to access the shared GCP database
3. Both use the **same** Google OAuth credentials

### Who Does What (First Time)

| Task | Who | Command |
|------|-----|---------|
| Create GCP Cloud SQL instance | Either (once) | GCP Console |
| Set up Google OAuth | Either (once) | Google Cloud Console |
| Run `seed_db.py` | Either (once) | `uv run python seed_db.py` |
| Share `.env` file | Owner → Collaborator | Secure channel |

### Daily Development

Both teammates can run the app simultaneously — they share the same database, so:
- ✅ Changes to data are visible to both
- ✅ Both can test the full flow
- ⚠️ Be careful with destructive operations (deleting users, etc.)

---

## 🔐 Google OAuth Setup

To enable Google Sign-In and Gmail sync:

1. Go to [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials)
2. Create an **OAuth 2.0 Client ID** (Web application)
3. Add **Authorized redirect URIs**:
   ```
   http://localhost:3000/api/auth/callback/google
   ```
4. Enable the **Gmail API** in your GCP project
5. Copy **Client ID** and **Client Secret** to `.env`

---

## 🧪 Testing the Setup

### Verify Backend
```bash
# Health check
curl http://127.0.0.1:8000/health
# Expected: {"status": "ok"}

# View API docs
open http://127.0.0.1:8000/docs
```

### Verify Frontend
1. Open http://localhost:3000
2. You should see the sign-in page
3. Sign in with Google
4. You should see the dashboard

### Dev Mode Testing (Without Google OAuth)

Set `DEV_MODE=true` in backend `.env`, then:

```bash
# Get stats with dev token
curl -H "Authorization: Bearer dev_anytoken" http://127.0.0.1:8000/api/stats

# List emails
curl -H "Authorization: Bearer dev_anytoken" http://127.0.0.1:8000/api/emails
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| **Database connection failed** | Check `DATABASE_URL`. Ensure GCP Cloud SQL is accessible. |
| **CORS errors** | Ensure `CORS_ALLOW_ORIGINS=http://localhost:3000` exactly. |
| **"Invalid token" errors** | Check `AUTH_GOOGLE_ID` matches in both frontend and backend. |
| **Port 8000/3000 in use** | Kill the process: `lsof -ti:8000 \| xargs kill` |
| **uv not found** | Run: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **pnpm not found** | Run: `npm install -g pnpm` |

---

## 📁 Project Structure

```
dec25_intern_B_security/
├── .env                    # Shared environment variables (DO NOT COMMIT)
├── example.env             # Template for .env
├── dashboard/              # Next.js frontend
│   ├── app/               # App router pages
│   ├── components/        # React components
│   └── lib/               # API utilities
├── dashboard-backend/      # FastAPI backend
│   ├── main.py            # API endpoints
│   ├── models.py          # Database models
│   └── database.py        # DB connection
└── agent-backend/          # Background worker
    ├── worker.py          # Email processing loop
    └── models.py          # Shared models
```

---

## 🏃 Running All Services

For full functionality, run these in separate terminals:

```bash
# Terminal 1: Backend API
cd dashboard-backend && uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2: Frontend
cd dashboard && pnpm dev

# Terminal 3: Worker (optional - processes emails in background)
cd agent-backend && uv run python -m worker
```
