# MailShield AI - Email Security Dashboard

This monorepo contains the following components:

- **dashboard**: Next.js Frontend
- **dashboard-backend**: Python/FastAPI Backend (Main Service)
- **agent-backend**: Python/FastAPI Backend (AI Agent Service)

## 🚀 Quick Start (One Shot)

You can start the entire project (frontend and backends) with a single command.

### Prerequisites

- **Node.js** (v18+)
- **Python** (v3.12+)
- **uv** (Python package manager)
- **npm** (Node package manager)

### Start Development

1.  **Install Dependencies** (First time only):
    ```bash
    # Install root dependencies (concurrently)
    npm install

    # Install frontend dependencies
    cd dashboard && npm install && cd ..
    
    # Install backend dependencies
    cd dashboard-backend && uv sync && cd ..
    cd agent-backend && uv sync && cd ..
    ```

2.  **Run Everything**:
    ```bash
    npm start
    ```
    *(Or `npm run dev`)*

This command will simultaneously start:
- The Next.js dashboard at [http://localhost:3000](http://localhost:3000)
- The Dashboard Backend
- The Agent Backend

## 🔐 Google Authentication Setup

To use Google Sign-In, you must configure your environment:

1.  Copy `.env.example` to `.env.local` in `dashboard/` (if not done automatically).
2.  Set your Google Client ID and Secret in `dashboard/.env.local`.
    ```env
    AUTH_GOOGLE_ID="your-client-id"
    AUTH_GOOGLE_SECRET="your-client-secret"
    AUTH_SECRET="your-secret-key"
    ```

## ⚙️ Backend Configuration

The backend services (`dashboard-backend` and `agent-backend`) also require configuration for Gmail API access and database connections.

1.  **Dashboard Backend**: Copy `dashboard-backend/.env.example` to `dashboard-backend/.env` and fill in your Gmail API credentials and database URL.
2.  **Agent Backend**: Copy `agent-backend/.env.example` to `agent-backend/.env` and configure accordingly.

**Required Variables**:
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`: For Gmail API access.
- `DATABASE_URL`: Connection string for the database (if used).
- `AUTH_SECRET`: Shared secret for security.
