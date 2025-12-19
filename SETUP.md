# Local Development Setup Guide

This guide will help you run the MailShieldAI project locally. The project consists of a FastAPI backend and a Next.js frontend.

## Prerequisites

- **Python 3.12+** (Backend)
- **Node.js 18+** (Frontend)
- **PostgreSQL** (Database)
- **uv** (Python package manager): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **pnpm** (Node package manager): `npm install -g pnpm`

---

## 1. Backend Setup (`dashboard-backend/`)

1.  **Navigate to the backend directory:**
    ```bash
    cd dashboard-backend
    ```

2.  **Configure Environment Variables:**
    Copy the example environment file from the root or create a new one:
    ```bash
    cp ../example.env .env
    ```

3.  **Update `.env`**:
    Open `.env` and ensure the configuration matches local needs (defaults to SQLite):
    ```properties
    # Default SQLite configuration
    DATABASE_URL=sqlite+aiosqlite:///./app.db
    
    # Dev mode to bypass strict Google Auth checks (optional)
    DEV_MODE=false
    
    # Google Auth Credentials (Required for Login)
    AUTH_GOOGLE_ID=your-google-client-id
    ```

4.  **Install Dependencies:**
    ```bash
    # Using uv (recommended)
    uv sync
    # OR using pip directly
    pip install -r requirements.txt
    ```

5.  **Initialize the Database:**
    Run the seeding script to create the database file and default organisation:
    ```bash
    # Using uv
    uv run python seed_db.py
    # OR using venv python
    ./.venv/bin/python seed_db.py
    ```

6.  **Run the Backend Server:**
    ```bash
    # Using uv
    uv run fastapi dev main.py
    # OR using venv python
    ./.venv/bin/python -m fastapi dev main.py
    ```
    - The server will start at `http://127.0.0.1:8000`.

7.  **Add Users:**
    Since Google Auth is used, you must explicitly add valid Google accounts to the database:
    ```bash
    # Get your Google ID from backend logs after a failed login attempt
    ./.venv/bin/python add_user.py "YOUR_GOOGLE_ID" "your.email@gmail.com" --admin
    ```

---

## 3. Frontend Setup (`dashboard/`)

1.  **Open a new terminal and navigate to the dashboard directory:**
    ```bash
    cd dashboard
    ```

2.  **Configure Environment Variables:**
    Create a `.env.local` file:
    ```bash
    touch .env.local
    ```
    Add the backend URL to it:
    ```properties
    NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
    ```

3.  **Install Dependencies:**
    ```bash
    pnpm install
    ```

4.  **Run the Frontend Development Server:**
    ```bash
    pnpm dev
    ```
    - The dashboard will be available at `http://localhost:3000`.

---

## Troubleshooting

- **Database Connection Failed**: Double-check your `DATABASE_URL` in `dashboard-backend/.env`. ensure the directory is writable for the SQLite file.
- **Authentication Errors**: If you see auth errors, ensure you have added your Google ID via `add_user.py`.
- **Port Conflicts**: Ensure ports 8000 (backend) and 3000 (frontend) are free.

---

## Verification

How to verify that everything is working properly:

### 1. Backend Verification
- Open your browser or use `curl` to check the health endpoint:
  - **URL**: `http://127.0.0.1:8000/health`
  - **Expected Output**: `{"status": "ok"}`
- Visit the API Documentation:
  - **URL**: `http://127.0.0.1:8000/docs`
  - **Success Check**: You should see the interactive Swagger UI with a list of endpoints.

### 2. Frontend Verification
- Open your browser and visit `http://localhost:3000`.
- **Success Check**:
  - You should see a "Sign in" page (if not logged in).
  - If `DEV_MODE=true` is set, you might still see "Sign in" because the frontend middleware enforces auth.
  - To fully verify the dashboard, you would need to complete the Google Sign-in flow (requires `DEV_MODE=false` and valid credentials) OR temporarily disable middleware.
