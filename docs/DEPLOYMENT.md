# FINSHIELD Deployment & Setup Guide

**Document Version:** 1.0.0-rc1  
**Operating Systems:** Linux, macOS, Windows (PowerShell)  
**Status:** Frozen for Release

---

## 1. Prerequisites & System Requirements

- **Python:** 3.11 or higher (Python 3.14 supported)
- **Node.js:** v18.0.0 or higher
- **Package Managers:** `pip` (Python), `npm` or `pnpm` (Node.js)
- **Database:** SQLite (default for development and Security Lab) or PostgreSQL 15+ (production)
- **Optional Cache:** Redis 7+ (for rate limiting and distributed caching)

---

## 2. Environment Configuration

Create a `.env` file inside the `backend/` directory based on the following template.

> [!CAUTION]
> **Security Notice:** Never commit actual secrets or API keys to source control. Use strong, randomly generated strings for all cryptographic secrets in production.

### Required Environment Variable Names

| Variable Name | Purpose | Example Value Format |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Runtime environment classification | `local`, `SANDBOX`, `production` |
| `DATABASE_URL` | Database connection string | `sqlite+aiosqlite:///./finshield.db` (or PostgreSQL async URL) |
| `SESSION_SECRET` | Session cookie encryption secret | 32+ character random secret string |
| `JWT_SECRET` | Secret key for signing user authentication JWTs | 32+ character random secret string |
| `ENCRYPTION_KEY` | Symmetric key for HMAC decision tokens & vault | 32+ character random secret string |
| `WEBHOOK_SIGNING_SECRET` | Secret key for signing outbound webhooks | 32+ character random secret string |
| `FRONTEND_URL` | Trusted frontend origin for CORS resolution | `http://localhost:5173` (or `http://localhost:8082`) |

### Optional LLM Provider Variables
FINSHIELD is provider-agnostic. Configure one or more of the following keys if enabling external agent reasoning loops:
- `LLM_PROVIDER`: Selected provider (e.g. `groq`, `openrouter`, `cerebras`, `openai`)
- `GROQ_API_KEY`: API key for Groq Cloud
- `GROQ_MODEL`: Model identifier (e.g. `openai/gpt-oss-20b`)
- `OPENROUTER_API_KEY`: API key for OpenRouter
- `CEREBRAS_API_KEY`: API key for Cerebras Inference
- `LLM_API_KEY`: API key for generic OpenAI-compatible providers

---

## 3. Database Initialization & Migrations

FINSHIELD manages schema versions via Alembic:

```bash
# Navigate to backend directory
cd backend

# Create and activate Python virtual environment
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r requirements.txt

# Execute all database migrations to latest schema
alembic upgrade head
```

---

## 4. Backend Service Startup

Start the FastAPI application via `uvicorn`:

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **API Gateway:** `http://localhost:8000`
- **Interactive Swagger Docs:** `http://localhost:8000/docs`
- **Health Check Endpoint:** `http://localhost:8000/health` (returns `{"status": "healthy"}`)

---

## 5. Frontend Service Startup

The frontend is a TanStack Start / Vite React application:

```bash
# In a separate terminal, navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start the Vite development server
npm run dev
```

- **Frontend Application:** `http://localhost:5173` (or port configured by Vite)
- **API Proxy:** The frontend connects to the backend at `http://localhost:8000`

---

## 6. Docker Compose Deployment (Alternative)

For containerized environments using PostgreSQL and Redis:

```bash
# From repository root
docker-compose up -d
```

Services initialized:
- `api`: FastAPI application on port `8000`
- `db`: PostgreSQL 15 on port `5432`
- `redis`: Redis 7 on port `6379`

---

## 7. Troubleshooting Common Issues

### 7.1 Cross-Origin Resource Sharing (CORS) Errors
- **Symptom:** Browser console reports blocked cross-origin requests.
- **Resolution:** Verify that the frontend host and port (e.g. `http://localhost:5173`, `http://localhost:8082`) match the entries listed in `backend/app/main.py` under `CORSMiddleware(allow_origins=[...])`.

### 7.2 Windows Console Unicode / Charmap Errors
- **Symptom:** `UnicodeEncodeError: 'charmap' codec can't encode character '\u20b9'` when displaying currency symbols (`₹`).
- **Resolution:** Set the Python I/O encoding in PowerShell before running commands:
  ```powershell
  $env:PYTHONIOENCODING = "utf-8"
  ```

### 7.3 SQLite Database File Locking
- **Symptom:** `sqlite3.OperationalError: database is locked` during concurrent test runs.
- **Resolution:** The Security Lab enforces a concurrency ceiling of 5 concurrent runs. Ensure that previous background tasks or hung test runners are terminated before starting new benchmark batches.

### 7.4 Port Collisions
- **Symptom:** `error: address already in use` on port 8000 or 5173.
- **Resolution:** Check running processes (`Get-Process -Name "*uvicorn*", "*node*"` on Windows or `lsof -i :8000` on Linux/macOS) and terminate stale processes before launching.

