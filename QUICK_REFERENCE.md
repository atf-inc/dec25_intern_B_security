# MailShieldAI - Quick Reference Guide

## 🚀 Common Commands

### Development

```bash
# Start Backend (Terminal 1)
cd apps/api
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Start Frontend (Terminal 2)
cd apps/web
pnpm dev

# Start Ingest Worker (Terminal 3)
cd apps/worker/ingest
uv run python main.py

# Start Decision Worker (Terminal 4)
cd apps/worker/decision
uv run python main.py

# Initialize Database
cd scripts
uv run python seed_db.py
```

### Testing

```bash
# Backend Health Check
curl http://127.0.0.1:8000/health

# API Documentation
open http://127.0.0.1:8000/docs

# Frontend
open http://localhost:3000

# Test with DEV_MODE token
curl -H "Authorization: Bearer dev_anytoken" http://127.0.0.1:8000/api/stats
```

### Database

```bash
# Connect to PostgreSQL
psql $DATABASE_URL

# View tables
\dt

# View users
SELECT * FROM users;

# View emails
SELECT id, sender, subject, status, risk_score FROM email_events LIMIT 10;

# Clear all emails
DELETE FROM email_events;
```

### Deployment

```bash
# Deploy all services to GCP
./deploy.sh

# Deploy individual services
gcloud run deploy mailshield-api --source apps/api --region asia-south1
gcloud run deploy mailshield-frontend --source apps/web --region asia-south1
gcloud run deploy mailshield-ingest --source apps/worker/ingest --region asia-south1
gcloud run deploy mailshield-decision --source apps/worker/decision --region asia-south1

# View logs
gcloud run logs read mailshield-api --region asia-south1
```

---

## 📁 File Locations

### Configuration
- **Environment Variables**: `.env` (root)
- **Backend Config**: `apps/api/main.py`
- **Frontend Config**: `apps/web/auth.ts`
- **Database Models**: `packages/shared/models.py`

### Key Files
- **API Routes**: `apps/api/routers/`
- **Gmail Service**: `apps/api/services/gmail.py` (937 lines!)
- **Auth Service**: `apps/api/services/auth.py`
- **Frontend Pages**: `apps/web/app/`
- **React Components**: `apps/web/components/`
- **Workers**: `apps/worker/ingest/main.py`, `apps/worker/decision/main.py`

---

## 🔑 Environment Variables

### Required for Backend
```bash
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
AUTH_GOOGLE_ID=xxx.apps.googleusercontent.com
AUTH_GOOGLE_SECRET=xxx
CORS_ALLOW_ORIGINS=http://localhost:3000
```

### Required for Frontend
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
AUTH_GOOGLE_ID=xxx.apps.googleusercontent.com
AUTH_GOOGLE_SECRET=xxx
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=xxx
```

### Optional
```bash
DEV_MODE=false
POLL_INTERVAL_SECONDS=5
BATCH_LIMIT=10
REDIS_URL=redis://localhost:6379/0
```

---

## 🔍 API Endpoints

### Authentication
```bash
# Get current user
GET /api/me
Authorization: Bearer {id_token}
```

### Emails
```bash
# List emails
GET /api/emails?status_filter=COMPLETED&limit=100&offset=0
Authorization: Bearer {id_token}

# Ingest email
POST /api/emails
Authorization: Bearer {id_token}
Content-Type: application/json
{
  "sender": "attacker@evil.com",
  "recipient": "victim@example.com",
  "subject": "Urgent: Reset your password",
  "body_preview": "Click here to reset..."
}

# Sync from Gmail
POST /api/emails/sync
Authorization: Bearer {id_token}
X-Google-Token: {access_token}
```

### Stats
```bash
# Dashboard statistics
GET /api/stats
Authorization: Bearer {id_token}
```

---

## 🗄️ Database Schema Quick Reference

### Users Table
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| google_id | VARCHAR | Google account ID (unique) |
| email | VARCHAR | Email address (unique) |
| name | VARCHAR | Display name |
| created_at | TIMESTAMP | Account creation time |

### Email Events Table
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to users |
| sender | VARCHAR | From address |
| recipient | VARCHAR | To address |
| subject | VARCHAR | Email subject |
| message_id | VARCHAR | Gmail message ID (unique) |
| body_preview | TEXT | First 200 chars of body |
| received_at | TIMESTAMP | Email timestamp |
| spf_status | VARCHAR | SPF check result |
| dkim_status | VARCHAR | DKIM check result |
| dmarc_status | VARCHAR | DMARC check result |
| sender_ip | VARCHAR | Originating IP |
| attachment_info | VARCHAR | Attachment filenames |
| threat_category | ENUM | PHISHING, MALWARE, SPAM, etc. |
| detection_reason | TEXT | Why flagged as threat |
| status | ENUM | PROCESSING, COMPLETED, FAILED |
| risk_score | INTEGER | 0-100 |
| risk_tier | ENUM | SAFE, CAUTIOUS, THREAT |
| analysis_result | JSON | Full analysis details |
| created_at | TIMESTAMP | Record creation |
| updated_at | TIMESTAMP | Last update |

---

## 🎨 Frontend Components

### Pages
- `/` - Landing page (redirects to `/emails` if authenticated)
- `/sign-in` - Google OAuth sign-in
- `/emails` - Email dashboard (main page)
- `/settings` - User settings

### Key Components
- `emails-page.tsx` - Email list with filters and sorting
- `overview-page.tsx` - Dashboard statistics and charts
- `settings-page.tsx` - User preferences
- `dashboard-layout.tsx` - Layout wrapper with sidebar
- `luffy/luffy-chatbot.tsx` - AI assistant chatbot

---

## 🔐 Authentication Flow

### Sign In
1. User clicks "Sign in with Google"
2. NextAuth redirects to Google OAuth
3. User grants Gmail permissions
4. Google returns tokens (access, refresh, id)
5. NextAuth stores in encrypted JWT cookie
6. User redirected to `/emails`

### API Requests
1. Frontend reads id_token from session
2. Sends `Authorization: Bearer {id_token}`
3. Backend verifies with Google
4. Auto-provisions user if first login
5. Returns user data

### Gmail Sync
1. Frontend reads access_token from session
2. Sends `X-Google-Token: {access_token}`
3. Backend calls Gmail API
4. Fetches recent messages
5. Stores in database

---

## 🐛 Troubleshooting

### Backend won't start
```bash
# Check DATABASE_URL
echo $DATABASE_URL

# Test database connection
psql $DATABASE_URL -c "SELECT 1"

# Check if port 8000 is in use
lsof -ti:8000 | xargs kill -9
```

### Frontend won't start
```bash
# Check if port 3000 is in use
lsof -ti:3000 | xargs kill -9

# Clear Next.js cache
rm -rf apps/web/.next

# Reinstall dependencies
cd apps/web
rm -rf node_modules
pnpm install
```

### CORS Errors
```bash
# Ensure CORS_ALLOW_ORIGINS matches frontend URL exactly
# Backend .env
CORS_ALLOW_ORIGINS=http://localhost:3000

# NOT: http://localhost:3000/
# NOT: https://localhost:3000
```

### Gmail Sync Fails
```bash
# Check Google token in browser console
console.log(session.accessToken)

# Verify scopes include gmail.readonly
# In auth.ts, check authorization.params.scope
```

### Database Errors
```bash
# Reset database (WARNING: deletes all data)
cd scripts
uv run python seed_db.py

# Or manually
psql $DATABASE_URL
DROP TABLE email_events;
DROP TABLE users;
\q

# Then re-run seed_db.py
```

---

## 📊 Risk Scoring

### Risk Tiers
| Score | Tier | Badge Color | Description |
|-------|------|-------------|-------------|
| 0-29 | SAFE | Green | Low risk, no suspicious indicators |
| 30-79 | CAUTIOUS | Yellow | Moderate risk, review recommended |
| 80-100 | THREAT | Red | High risk, likely phishing/malware |

### Threat Categories
- **NONE** - No threat detected
- **PHISHING** - Credential theft attempt
- **MALWARE** - Malicious attachment/link
- **SPAM** - Unsolicited bulk email
- **BEC** - Business Email Compromise
- **SPOOFING** - Sender impersonation
- **SUSPICIOUS** - Unusual patterns

### Risk Indicators
- ❌ SPF/DKIM/DMARC failures
- ❌ Suspicious sender IP
- ❌ Risky file extensions (.exe, .scr, .vbs)
- ❌ Shortened URLs
- ❌ Mismatched display name and email
- ❌ Urgent language ("Act now!", "Verify account")
- ❌ Unusual sender domain

---

## 🔧 Useful SQL Queries

```sql
-- Top 10 riskiest emails
SELECT sender, subject, risk_score, threat_category 
FROM email_events 
ORDER BY risk_score DESC 
LIMIT 10;

-- Emails by status
SELECT status, COUNT(*) 
FROM email_events 
GROUP BY status;

-- Emails by risk tier
SELECT risk_tier, COUNT(*) 
FROM email_events 
GROUP BY risk_tier;

-- Recent threats
SELECT sender, subject, threat_category, detection_reason 
FROM email_events 
WHERE threat_category != 'NONE' 
ORDER BY created_at DESC 
LIMIT 20;

-- Failed authentication checks
SELECT sender, spf_status, dkim_status, dmarc_status 
FROM email_events 
WHERE spf_status = 'FAIL' OR dkim_status = 'FAIL' OR dmarc_status = 'FAIL';

-- Emails with attachments
SELECT sender, subject, attachment_info 
FROM email_events 
WHERE attachment_info IS NOT NULL;
```

---

## 📦 Dependencies

### Backend (Python)
- fastapi[standard] >= 0.124.2
- sqlmodel >= 0.0.27
- asyncpg >= 0.31.0
- psycopg2-binary >= 2.9.9
- python-dotenv >= 1.0.1
- google-auth >= 2.45.0
- google-api-python-client >= 2.187.0
- redis >= 5.0.0

### Frontend (Node.js)
- next: 16.0.10
- react: 19.2.0
- next-auth: 5.0.0-beta.30
- tailwindcss: 4.1.9
- @radix-ui/* (various)
- framer-motion: 12.23.26
- recharts: 2.15.4

---

## 🌐 URLs

### Local Development
- Frontend: http://localhost:3000
- Backend API: http://127.0.0.1:8000
- API Docs: http://127.0.0.1:8000/docs
- Redoc: http://127.0.0.1:8000/redoc

### Production (GCP)
- Frontend: https://mailshield-frontend-xxx.run.app
- Backend: https://mailshield-api-xxx.run.app
- Workers: (internal, no public URL)

---

## 📝 Git Workflow

```bash
# Create feature branch
git checkout -b feature/amazing-feature

# Make changes
git add .
git commit -m "Add amazing feature"

# Push to remote
git push origin feature/amazing-feature

# Create Pull Request on GitHub

# After merge, update main
git checkout main
git pull origin main
```

---

## 🎯 Quick Tips

1. **Always use `uv` for Python** - Faster than pip
2. **Use `pnpm` for Node.js** - Faster than npm
3. **Check logs first** - Most errors are in logs
4. **Test with DEV_MODE** - Bypass OAuth for quick testing
5. **Use API docs** - http://localhost:8000/docs is your friend
6. **Clear cache** - When in doubt, clear `.next` and `node_modules`
7. **Check environment** - Most issues are missing env vars
8. **Read error messages** - They're usually helpful!

---

**Last Updated:** 2025-12-22  
**Version:** 0.2.0
