# MailShieldAI API

FastAPI backend for the MailShieldAI dashboard.

## Project Structure

This API is part of the MailShieldAI monorepo:

- **apps/api/** - This API application
- **packages/shared/** - Shared modules (database, models, constants)
- **scripts/** - Utility scripts (migration, seeding)

## Dependencies

The API relies on:
- `packages.shared.database` - Database connection and session management
- `packages.shared.models` - SQLModel definitions for all data models

## Running the API

```bash
cd apps/api
uv run fastapi dev main.py
```

## Development

The API uses a router-based architecture with modularized endpoints:
- `routers/emails.py` - Email-related endpoints (planned)
- `routers/stats.py` - Statistics endpoints (planned)
- `routers/users.py` - User management endpoints (planned)
