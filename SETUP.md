# Setup Guide — How to Run the Application

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker Desktop | Latest | Runs PostgreSQL, Redis, Backend API, Celery containers |
| Node.js | 18+ | Runs the Next.js frontend |
| npm | 9+ | Installs frontend dependencies |
| Git | Latest | Version control |

You do **not** need to install Python, PostgreSQL, or Redis locally — Docker handles all of that.

---

## Step 1: Clone the Repositories

```bash
# Clone Backend
git clone https://github.com/ragul666/workflow_management_be.git

# Clone Frontend
git clone https://github.com/ragul666/workflow_management_fe.git
```

---

## Step 2: Backend Setup (Docker)

Everything runs inside Docker containers. No local Python installation needed.

### 2.1 Create the environment file

```bash
cd workflow_management_be
cp .env.example .env
```

### 2.2 Edit `.env` with your values

Open `.env` and update these fields:

```bash
# These are already set correctly for Docker — no changes needed:
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/compliance_db
SYNC_DATABASE_URL=postgresql://postgres:postgres@db:5432/compliance_db
REDIS_URL=redis://redis:6379/0

# Generate a random 32+ character string for SECRET_KEY:
SECRET_KEY=your-random-secret-key-at-least-32-characters-long

# Algorithm and token expiry — leave as defaults:
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# OpenAI API Key (required for AI summary feature):
# Get it from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Frontend URL for CORS — leave as default:
CORS_ORIGINS=http://localhost:3000
```

**Important notes:**
- The `DATABASE_URL` uses `db` (not `localhost`) because inside Docker, containers talk to each other by service name
- The `OPENAI_API_KEY` is only needed if you want to use the AI summary feature. The app works without it — the AI button will just return an error
- Generate a `SECRET_KEY` by running: `openssl rand -hex 32`

### 2.3 Start all backend services

```bash
docker-compose up --build -d
```

This starts 5 containers:
- **db** — PostgreSQL database (port 5432)
- **redis** — Redis message broker (port 6379)
- **api** — FastAPI backend (port 8000)
- **celery_worker** — Background task processor
- **celery_beat** — Periodic task scheduler

### 2.4 Wait for services to be ready

```bash
# Wait ~10 seconds for PostgreSQL to initialize
sleep 10

# Verify all containers are running
docker-compose ps
```

You should see all 5 containers with status `Up` or `Running`.

### 2.5 Run database migrations

```bash
docker-compose exec api alembic upgrade head
```

This creates all database tables (tenants, users, roles, issues, etc.).

### 2.6 Seed demo data

```bash
docker-compose exec api python seed.py
```

This creates:
- 2 tenant organizations (MedTech Corp, PharmaCo)
- 5 demo users with different roles
- 4 roles (admin, manager, reviewer, user) with 12 permissions
- 6 workflow states and transitions
- Sample compliance issues

### 2.7 Verify backend is working

```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy"}

# Test login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@medtech.com","password":"admin123"}'
# Should return: {"access_token":"...", "refresh_token":"...", "token_type":"bearer"}
```

**API Documentation**: http://localhost:8000/docs (Swagger UI)

---

## Step 3: Frontend Setup

### 3.1 Navigate to the frontend directory

```bash
cd workflow_management_fe
```

> If you cloned both repos side by side, go back first: `cd ../workflow_management_fe`

### 3.2 Create the environment file

```bash
cp .env.local.example .env.local
```

The defaults are correct — no changes needed unless you changed backend ports:
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

### 3.3 Install dependencies

```bash
npm install
```

### 3.4 Start the development server

```bash
npm run dev
```

The frontend will be available at: **http://localhost:3000**

---

## Step 4: Login and Test

Open http://localhost:3000 in your browser.

### Demo Accounts

| Email | Password | Role |
|-------|----------|------|
| admin@medtech.com | admin123 | Admin |
| manager@medtech.com | manager123 | Manager |
| reviewer@medtech.com | reviewer123 | Reviewer |
| user@medtech.com | user123 | User |

---

## Common Commands

### Backend

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Stop and remove all data (reset database)
docker-compose down -v

# View API logs
docker-compose logs -f api

# View all logs
docker-compose logs -f

# Rebuild after code changes
docker-compose up --build -d

# Run migrations
docker-compose exec api alembic upgrade head

# Re-seed data (after reset)
docker-compose exec api python seed.py

# Open database shell
docker-compose exec db psql -U postgres compliance_db
```

### Frontend

```bash
# Start development server
npm run dev

# Production build
npm run build

# Start production server
npm start

# Clean reinstall
rm -rf .next node_modules package-lock.json && npm install
```

---

## Troubleshooting

### Backend won't start
```bash
# Check container status
docker-compose ps

# Check API logs for errors
docker-compose logs api

# Restart everything fresh
docker-compose down -v
docker-compose up --build -d
sleep 10
docker-compose exec api alembic upgrade head
docker-compose exec api python seed.py
```

### Database connection error
- Make sure Docker Desktop is running
- Check that port 5432 is not used by another PostgreSQL instance
- Inside Docker, the DB host is `db`, not `localhost`

### Login returns 500 error
- Check API logs: `docker-compose logs api`
- Make sure you ran `seed.py` to create demo users
- Make sure the API container is healthy: `docker-compose ps`

### Frontend can't connect to backend
- Verify backend is running: `curl http://localhost:8000/health`
- Check `.env.local` has correct `NEXT_PUBLIC_API_URL`
- Check browser console for CORS errors — verify `CORS_ORIGINS` in backend `.env`

### Port already in use
- Backend: Change port in `docker-compose.yml` under `api.ports`
- Frontend: Next.js auto-picks next available port (3001, 3002, etc.)

### AI Summary not working
- Verify `OPENAI_API_KEY` is set in `.env`
- Check your OpenAI account has API credits
- Check API logs for OpenAI errors: `docker-compose logs api`
