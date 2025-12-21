"""MailShieldAI Dashboard API - Single User Architecture."""

from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from packages.shared.database import init_db
from apps.api.routers import auth, emails, stats

load_dotenv()

logger = logging.getLogger(__name__)


def _validate_cors_config() -> list[str]:
    """Validate CORS configuration and return parsed origins list.

    Fails fast if credentials are enabled with wildcard origins (insecure).
    """
    cors_origins_raw = os.getenv('CORS_ALLOW_ORIGINS', '').strip()
    allow_credentials = True  # We always use credentials for auth

    if not cors_origins_raw:
        logger.error(
            'CORS_ALLOW_ORIGINS environment variable is not set. '
            'Please set it to a comma-separated list of allowed origins.'
        )
        sys.exit(1)

    # Parse comma-separated origins, trim whitespace
    origins = [origin.strip() for origin in cors_origins_raw.split(',') if origin.strip()]

    if not origins:
        logger.error('CORS_ALLOW_ORIGINS is empty after parsing.')
        sys.exit(1)

    # Check for wildcard with credentials - this is invalid per CORS spec
    if '*' in origins and allow_credentials:
        logger.error(
            "SECURITY ERROR: CORS_ALLOW_ORIGINS='*' with allow_credentials=True is invalid. "
            'Browsers will reject this configuration. '
            "Please specify explicit origins (e.g., 'http://localhost:3000,https://app.example.com')."
        )
        sys.exit(1)

    logger.info(f'CORS configured for origins: {origins}')
    return origins


# Validate CORS configuration before app creation
_cors_origins = _validate_cors_config()

app = FastAPI(title='MailShieldAI Dashboard API', version='0.2.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with CORS headers."""
    logger.error(f'Global exception: {exc}', exc_info=True)
    return JSONResponse(
        status_code=500,
        content={'detail': 'Internal Server Error', 'error': str(exc)},
        headers={
            'Access-Control-Allow-Origin': request.headers.get('origin', '*'),
            'Access-Control-Allow-Credentials': 'true',
        },
    )


GOOGLE_CLIENT_ID = os.getenv('AUTH_GOOGLE_ID')
DEV_MODE = os.getenv('DEV_MODE', 'false').lower() in ('true', '1', 'yes')

if DEV_MODE:
    logger.warning('DEV_MODE is enabled. Auth verification may be skipped. DO NOT use this setting in production!')
elif not GOOGLE_CLIENT_ID:
    raise RuntimeError('AUTH_GOOGLE_ID environment variable is not set. Service cannot start in production mode.')


@app.on_event('startup')
async def on_startup() -> None:
    """Initialize database on startup."""
    await init_db()


@app.get('/health')
async def health() -> dict:
    """Health check endpoint."""
    return {'status': 'ok'}


# Register Routers
app.include_router(auth.router, prefix='/api', tags=['auth'])
app.include_router(emails.router, prefix='/api/emails', tags=['emails'])
app.include_router(stats.router, prefix='/api', tags=['stats'])
