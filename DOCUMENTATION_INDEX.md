# 📚 MailShieldAI - Documentation Index

Welcome to the complete documentation for **MailShieldAI**, an AI-powered email security platform.

---

## 📖 Documentation Files

### 1. **README.md** - Quick Start Guide
**Purpose:** Get up and running in 5 minutes  
**Audience:** New developers, quick reference  
**Contents:**
- Project overview and features
- Quick start instructions
- Basic architecture diagram
- API endpoint summary
- License and contributing info

👉 **Start here if you're new to the project**

---

### 2. **SETUP.md** - Detailed Setup Instructions
**Purpose:** Complete local development setup  
**Audience:** Team members setting up for the first time  
**Contents:**
- Prerequisites and tool installation
- Step-by-step backend setup
- Step-by-step frontend setup
- Worker setup (optional)
- Team collaboration notes
- Google OAuth configuration
- Troubleshooting common issues

👉 **Use this for your first-time setup**

---

### 3. **REPOSITORY_OVERVIEW.md** - Complete Architecture Guide
**Purpose:** Deep understanding of the entire codebase  
**Audience:** Developers who need to understand the system  
**Contents:**
- Comprehensive architecture overview
- Technology stack details
- Complete directory structure
- Core component descriptions
- Database schema
- API endpoints reference
- Authentication & security
- Deployment guide
- Development workflow

👉 **Read this to understand the complete system** (THIS DOCUMENT!)

---

### 4. **QUICK_REFERENCE.md** - Developer Cheat Sheet
**Purpose:** Quick lookup for common tasks  
**Audience:** Daily development work  
**Contents:**
- Common commands (start servers, deploy, etc.)
- File locations
- Environment variables
- API endpoints with examples
- Database schema quick reference
- Frontend components
- SQL queries
- Troubleshooting tips

👉 **Bookmark this for daily development**

---

### 5. **DATA_FLOW.md** - Processing Pipeline Guide
**Purpose:** Understand how emails flow through the system  
**Audience:** Developers working on workers or analysis  
**Contents:**
- Complete email processing flow diagram
- Detailed component interactions
- State transitions
- Performance metrics
- Security considerations
- Future enhancements

👉 **Read this to understand email processing**

---

### 6. **example.env** - Environment Configuration Template
**Purpose:** Template for environment variables  
**Audience:** Anyone setting up the project  
**Contents:**
- All required environment variables
- Descriptions and examples
- Security warnings
- Default values

👉 **Copy this to `.env` and fill in your values**

---

## 🗺️ Navigation Guide

### I want to...

#### **Get started quickly**
1. Read **README.md** (5 min)
2. Follow **SETUP.md** (30 min)
3. Start coding!

#### **Understand the architecture**
1. Read **REPOSITORY_OVERVIEW.md** (30 min)
2. Review **DATA_FLOW.md** (20 min)
3. Explore the codebase with context

#### **Work on a specific feature**
1. Use **QUICK_REFERENCE.md** for commands
2. Check **REPOSITORY_OVERVIEW.md** for component details
3. Review **DATA_FLOW.md** if working on email processing

#### **Debug an issue**
1. Check **QUICK_REFERENCE.md** troubleshooting section
2. Review **SETUP.md** for configuration issues
3. Check logs (see **QUICK_REFERENCE.md** for log commands)

#### **Deploy to production**
1. Read **REPOSITORY_OVERVIEW.md** deployment section
2. Run `./deploy.sh` (see **QUICK_REFERENCE.md**)
3. Follow post-deployment steps in **SETUP.md**

---

## 📊 Key Concepts

### Architecture Layers

```
┌─────────────────────────────────────────┐
│         Frontend (Next.js)              │ ← User Interface
├─────────────────────────────────────────┤
│         API (FastAPI)                   │ ← REST Endpoints
├─────────────────────────────────────────┤
│    Workers (Ingest + Decision)          │ ← Email Processing
├─────────────────────────────────────────┤
│  Database (PostgreSQL) + Queue (Redis)  │ ← Data Storage
└─────────────────────────────────────────┘
```

### Data Flow

```
Gmail → Ingest Worker → Decision Worker → Database → Frontend
         ↓                ↓                 ↓
      Extract         Analyze           Update
      Metadata        Risk              Display
```

### Key Technologies

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js 16 + React 19 | User interface |
| API | FastAPI + SQLModel | REST endpoints |
| Workers | FastAPI + Gmail API | Email processing |
| Database | PostgreSQL (Cloud SQL) | Data storage |
| Queue | Redis | Job processing |
| Auth | NextAuth.js + Google OAuth | Authentication |
| Deploy | GCP Cloud Run | Serverless hosting |

---

## 🎯 Common Tasks

### Starting Development

```bash
# Terminal 1: Backend
cd apps/api && uv run uvicorn main:app --reload

# Terminal 2: Frontend
cd apps/web && pnpm dev

# Terminal 3: Workers (optional)
cd apps/worker/ingest && uv run python main.py
```

### Testing

```bash
# Health check
curl http://127.0.0.1:8000/health

# API docs
open http://127.0.0.1:8000/docs

# Frontend
open http://localhost:3000
```

### Deployment

```bash
# Deploy all services
./deploy.sh

# Or deploy individually
gcloud run deploy mailshield-api --source apps/api
gcloud run deploy mailshield-frontend --source apps/web
```

---

## 🔍 Code Locations

### Backend (Python)
- **API Entry:** `apps/api/main.py`
- **Routes:** `apps/api/routers/`
- **Gmail Service:** `apps/api/services/gmail.py` (937 lines!)
- **Auth Service:** `apps/api/services/auth.py`
- **Models:** `packages/shared/models.py`
- **Database:** `packages/shared/database.py`

### Frontend (TypeScript)
- **Pages:** `apps/web/app/`
- **Components:** `apps/web/components/`
- **API Client:** `apps/web/lib/api.ts`
- **Auth Config:** `apps/web/auth.ts`

### Workers (Python)
- **Ingest:** `apps/worker/ingest/main.py`
- **Decision:** `apps/worker/decision/main.py`

---

## 🔐 Security Highlights

### Authentication
- Google OAuth 2.0 with Gmail scopes
- NextAuth.js for session management
- JWT tokens with encryption
- Auto-provisioning on first login

### Email Security
- SPF/DKIM/DMARC validation
- Sender IP tracking
- URL extraction and analysis
- Attachment metadata (no content storage)
- Sandbox analysis for risky files

### Infrastructure
- CORS with strict origin validation
- SSL/TLS for all connections
- Secret Manager for credentials
- Cloud SQL with private IP

---

## 📈 Performance

### Typical Processing Times
- **Gmail Sync:** 1-3 seconds
- **Static Analysis:** < 100ms
- **Sandbox Analysis:** 30s - 5min (if needed)
- **Database Update:** < 100ms

### Optimization Strategies
- Async processing with workers
- Redis queue for job management
- Connection pooling for database
- Lazy attachment fetching
- Batch processing

---

## 🐛 Troubleshooting

### Common Issues

1. **CORS Errors**
   - Check `CORS_ALLOW_ORIGINS` matches frontend URL exactly
   - See **QUICK_REFERENCE.md** → Troubleshooting

2. **Database Connection Failed**
   - Verify `DATABASE_URL` in `.env`
   - Check Cloud SQL accessibility
   - See **SETUP.md** → Troubleshooting

3. **Gmail Sync Fails**
   - Check Google token expiry
   - Verify scopes in `auth.ts`
   - See **REPOSITORY_OVERVIEW.md** → Authentication

4. **Port Already in Use**
   ```bash
   lsof -ti:8000 | xargs kill -9
   ```

---

## 🚀 Next Steps

### For New Developers
1. ✅ Read **README.md**
2. ✅ Follow **SETUP.md**
3. ✅ Explore **REPOSITORY_OVERVIEW.md**
4. ✅ Bookmark **QUICK_REFERENCE.md**
5. ✅ Start coding!

### For Experienced Developers
1. ✅ Skim **REPOSITORY_OVERVIEW.md**
2. ✅ Review **DATA_FLOW.md**
3. ✅ Use **QUICK_REFERENCE.md** as needed
4. ✅ Dive into the code!

### For DevOps/Deployment
1. ✅ Read **REPOSITORY_OVERVIEW.md** → Deployment
2. ✅ Review **SETUP.md** → GCP Configuration
3. ✅ Run `./deploy.sh`
4. ✅ Configure Cloud SQL and secrets

---

## 📞 Support

### Documentation Issues
- File an issue on GitHub
- Tag with `documentation` label

### Code Issues
- Check **QUICK_REFERENCE.md** → Troubleshooting
- Review logs (see **QUICK_REFERENCE.md**)
- File an issue with logs and steps to reproduce

### Feature Requests
- Review **DATA_FLOW.md** → Future Enhancements
- File an issue with `enhancement` label

---

## 📝 Contributing

1. Read **README.md** → Contributing section
2. Follow **SETUP.md** to set up locally
3. Create a feature branch
4. Make changes
5. Test thoroughly
6. Submit a Pull Request

---

## 🎓 Learning Path

### Week 1: Setup & Basics
- [ ] Complete **SETUP.md**
- [ ] Read **README.md**
- [ ] Explore frontend components
- [ ] Test API endpoints

### Week 2: Architecture
- [ ] Read **REPOSITORY_OVERVIEW.md**
- [ ] Review **DATA_FLOW.md**
- [ ] Understand database schema
- [ ] Explore worker code

### Week 3: Development
- [ ] Use **QUICK_REFERENCE.md** daily
- [ ] Fix a small bug
- [ ] Add a feature
- [ ] Write tests

### Week 4: Advanced
- [ ] Optimize performance
- [ ] Deploy to GCP
- [ ] Add monitoring
- [ ] Contribute to docs

---

## 📚 Additional Resources

### External Documentation
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Next.js Docs](https://nextjs.org/docs)
- [NextAuth.js Docs](https://next-auth.js.org/)
- [Gmail API Docs](https://developers.google.com/gmail/api)
- [Google Cloud Docs](https://cloud.google.com/docs)

### Tools
- [uv (Python)](https://github.com/astral-sh/uv)
- [pnpm (Node.js)](https://pnpm.io/)
- [Radix UI](https://www.radix-ui.com/)
- [Tailwind CSS](https://tailwindcss.com/)

---

## 🏆 Best Practices

### Code Quality
- ✅ Use type hints (Python) and TypeScript
- ✅ Write docstrings for all functions
- ✅ Follow async/await patterns
- ✅ Handle errors gracefully
- ✅ Log important events

### Security
- ✅ Never commit `.env` files
- ✅ Validate all user input
- ✅ Use parameterized SQL queries
- ✅ Verify tokens on every request
- ✅ Use HTTPS in production

### Performance
- ✅ Use async I/O
- ✅ Implement connection pooling
- ✅ Cache frequently accessed data
- ✅ Batch database operations
- ✅ Monitor and optimize slow queries

---

## 📊 Project Stats

- **Total Lines of Code:** ~50,000+
- **Languages:** Python, TypeScript, SQL
- **Components:** 4 (API, Frontend, 2 Workers)
- **Database Tables:** 2 (Users, EmailEvents)
- **API Endpoints:** 8+
- **Documentation Pages:** 6

---

## 🎉 You're Ready!

You now have access to complete documentation for MailShieldAI. Use the navigation guide above to find what you need, and don't hesitate to contribute improvements to these docs!

**Happy coding! 🚀**

---

**Last Updated:** 2025-12-22  
**Version:** 0.2.0  
**Maintainer:** MailShieldAI Team
