# AI-Powered Compliance & Workflow Management System

A multi-tenant Compliance & Issue Management Platform designed for regulated industries (MedTech, Pharma, Manufacturing). The system manages issues through configurable workflows, tracks SLA compliance, maintains immutable audit trails, and integrates AI for intelligent root-cause summaries.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  Next.js 14 (App Router) + Tailwind + Zustand + React Query │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────┐  │
│  │  Login   │ │Dashboard │ │  Issues   │ │ Workflow     │  │
│  │  Page    │ │  Page    │ │ List/Det  │ │ Admin Page   │  │
│  └──────────┘ └──────────┘ └───────────┘ └──────────────┘  │
│       │             │             │              │           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  API Layer (Axios) + WebSocket Hook + Auth Store    │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────┬───────────────┬───────────────────────┘
                       │ REST API      │ WebSocket
┌──────────────────────▼───────────────▼───────────────────────┐
│                        BACKEND                                │
│                    FastAPI (Async)                             │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    API Layer                             │ │
│  │  /auth  /issues  /workflow  /dashboard  /ai  /ws        │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                  Service Layer                           │ │
│  │  WorkflowEngine  SLAService  AuditService  AIService    │ │
│  │  EventBus  WebSocketManager                             │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                  Domain Layer                            │ │
│  │  Tenant  User  Role  Permission  Issue  WorkflowState   │ │
│  │  WorkflowTransition  AuditLog  AISummary  Attachment    │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │               Infrastructure Layer                       │ │
│  │  SQLAlchemy (Async)  JWT Auth  RBAC  Tenant Middleware   │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────┬──────────────┬──────────────┬─────────────────────────┘
       │              │              │
┌──────▼──────┐ ┌─────▼─────┐ ┌─────▼─────┐
│ PostgreSQL  │ │   Redis   │ │  OpenAI   │
│  (Primary)  │ │  (Cache/  │ │  (LLM)    │
│             │ │  Broker)  │ │           │
└─────────────┘ └─────┬─────┘ └───────────┘
                      │
                ┌─────▼─────┐
                │  Celery   │
                │  Worker   │
                │ (SLA Jobs)│
                └───────────┘
```

## Tech Stack

| Layer     | Technology                                        |
|-----------|---------------------------------------------------|
| Frontend  | Next.js 14, TypeScript, Tailwind CSS, Zustand, React Query, Recharts, Lucide |
| Backend   | Python 3.11+, FastAPI, SQLAlchemy (async), Pydantic v2 |
| Database  | PostgreSQL 15                                     |
| Cache     | Redis 7                                           |
| Queue     | Celery + Redis broker                             |
| AI        | OpenAI GPT-4 (configurable)                       |
| Auth      | JWT (access + refresh tokens), RBAC               |
| Realtime  | WebSockets (native FastAPI)                       |
| DevOps    | Docker, Docker Compose, Alembic                   |

## Features

- **Multi-Tenancy**: Shared DB with `tenant_id` column, middleware-injected context
- **JWT Authentication**: Access + refresh token flow with auto-renewal
- **RBAC**: Fine-grained role-based access (admin, manager, reviewer, user)
- **Configurable Workflow Engine**: DB-driven states and transitions, no hardcoding
- **SLA Tracking**: Due dates, countdown timers, Celery-based overdue detection
- **Audit Trail**: Immutable logs with user, timestamp, old/new values
- **Real-Time Updates**: WebSocket push for live issue status changes
- **AI Integration**: LLM-powered root cause analysis with versioned summaries
- **Dashboard**: Pie/bar charts, SLA breach %, avg resolution time

## Project Structure

```
workflow_management/
├── workflow_management_be/          # Backend
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py             # Auth/RBAC dependencies
│   │   │   └── routes/             # auth, issues, workflow, dashboard, ai
│   │   ├── core/
│   │   │   ├── config.py           # Settings from env
│   │   │   ├── database.py         # Async SQLAlchemy
│   │   │   ├── security.py         # JWT + password hashing
│   │   │   ├── rbac.py             # Permission decorators
│   │   │   └── tenant.py           # Tenant context var
│   │   ├── models/                 # SQLAlchemy models
│   │   ├── schemas/                # Pydantic schemas
│   │   ├── services/               # Business logic
│   │   ├── tasks/                  # Celery tasks
│   │   ├── utils/                  # Enums, helpers
│   │   └── main.py                 # FastAPI app entry
│   ├── alembic/                    # DB migrations
│   ├── seed.py                     # Sample data seeder
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
├── workflow_management_fe/          # Frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx          # Root layout
│   │   │   ├── page.tsx            # Redirect
│   │   │   ├── login/page.tsx      # Login page
│   │   │   └── (protected)/        # Auth-guarded routes
│   │   │       ├── dashboard/      # Dashboard with charts
│   │   │       ├── issues/         # Issue list + detail
│   │   │       └── admin/workflow/ # Workflow config
│   │   ├── components/             # Sidebar, AuthGuard
│   │   ├── hooks/                  # useWebSocket
│   │   ├── services/               # API client layer
│   │   ├── store/                  # Zustand stores
│   │   └── types/                  # TypeScript types
│   ├── package.json
│   ├── tailwind.config.ts
│   └── tsconfig.json
└── README.md
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ and npm

### Backend

```bash
cd workflow_management_be

# Start all services (PostgreSQL, Redis, API, Celery)
docker-compose up --build -d

# Run migrations
docker-compose exec api alembic upgrade head

# Seed sample data
docker-compose exec api python seed.py
```

The API will be available at `http://localhost:8000`.
API docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd workflow_management_fe

npm install
npm run dev
```

The frontend will be available at `http://localhost:3000`.

### Demo Accounts

| Email                    | Password     | Role     |
|--------------------------|------------- |----------|
| admin@medtech.com        | admin123     | Admin    |
| manager@medtech.com      | manager123   | Manager  |
| reviewer@medtech.com     | reviewer123  | Reviewer |
| user@medtech.com         | user123      | User     |

## API Endpoints

| Method | Endpoint                        | Description              |
|--------|--------------------------------|--------------------------|
| POST   | /api/v1/auth/login             | Login                    |
| POST   | /api/v1/auth/register          | Register user            |
| POST   | /api/v1/auth/refresh           | Refresh token            |
| GET    | /api/v1/auth/me                | Current user             |
| GET    | /api/v1/issues                 | List issues (paginated)  |
| POST   | /api/v1/issues                 | Create issue             |
| GET    | /api/v1/issues/:id             | Get issue detail         |
| PATCH  | /api/v1/issues/:id             | Update issue             |
| POST   | /api/v1/issues/:id/transition  | Transition issue state   |
| GET    | /api/v1/issues/:id/transitions | Available transitions    |
| GET    | /api/v1/issues/:id/audit       | Issue audit trail        |
| GET    | /api/v1/issues/:id/sla         | SLA countdown            |
| GET    | /api/v1/workflow/states        | List workflow states     |
| POST   | /api/v1/workflow/states        | Create workflow state    |
| GET    | /api/v1/workflow/transitions   | List transitions         |
| POST   | /api/v1/workflow/transitions   | Create transition        |
| GET    | /api/v1/dashboard/metrics      | Dashboard analytics      |
| POST   | /api/v1/ai/generate-summary    | Generate AI summary      |
| GET    | /api/v1/ai/summaries/:id       | Get issue summaries      |
| WS     | /ws/:tenant_id                 | Real-time updates        |

## Environment Variables

### Backend (.env)

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/compliance_db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=<your-secret-key>
OPENAI_API_KEY=<your-openai-key>
CORS_ORIGINS=http://localhost:3000
```

### Frontend (.env.local)

```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

## Workflow Engine

The workflow is fully configurable via the database. Default states:

```
Draft → Submitted → Under Review → Approved → Closed
                                 ↘ Rejected → Closed
```

Transitions are role-gated. Only users with the correct role assigned in the transition config can perform that state change.

## Event-Driven Architecture

Internal events (`IssueCreated`, `IssueUpdated`, `SLABreached`) propagate through an in-memory event bus, triggering:

- WebSocket broadcasts to connected clients
- Audit log entries
- SLA recalculations
