# Router Automation & Management Portal

A professional network operations center (NOC) dashboard for network engineers to manage multi-vendor routers.

## Features

- **Multi-vendor support**: Cisco IOS/IOS-XE, Juniper JunOS, MikroTik RouterOS, Huawei, Arista EOS, VyOS
- **Router Inventory**: Add, edit, delete routers with encrypted credentials storage
- **Config Backup & Restore**: Manual and scheduled configuration backups with version history
- **Config Templates**: Jinja2-based configuration templates with variable substitution
- **Live Terminal**: Browser-based SSH terminal with xterm.js
- **Scheduled Jobs**: Automate backup and command execution with cron-like scheduling
- **Dashboard**: Overview of network status, recent backups, and quick actions

## Tech Stack

- **Frontend**: Vue 3 + Vite + Tailwind CSS + Pinia + xterm.js
- **Backend**: FastAPI + Python 3.11+
- **Database**: MySQL 8.0
- **Task Queue**: Celery + Redis (for scheduled jobs)
- **SSH**: Paramiko

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Manual Setup

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/router_mgmt
export SECRET_KEY=your-secret-key
export ENCRYPTION_KEY=32-byte-encryption-key-here!!

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/routers` | List all routers |
| POST | `/api/routers` | Add new router |
| GET | `/api/routers/{id}` | Get router details |
| PUT | `/api/routers/{id}` | Update router |
| DELETE | `/api/routers/{id}` | Delete router |
| POST | `/api/routers/{id}/backup` | Trigger backup |
| POST | `/api/routers/{id}/connect` | Test connection |
| POST | `/api/routers/{id}/command` | Execute command |
| GET | `/api/backups` | List all backups |
| POST | `/api/backups/{id}/restore` | Restore backup |
| GET | `/api/templates` | List templates |
| POST | `/api/templates/{id}/render` | Render template |
| GET | `/api/jobs` | List scheduled jobs |
| POST | `/api/jobs/{id}/run` | Run job now |
| GET | `/api/dashboard/stats` | Dashboard statistics |

## Supported Vendors

- Cisco IOS
- Cisco IOS-XE
- Juniper JunOS
- MikroTik RouterOS
- Huawei
- Arista EOS
- VyOS
- Generic (SSH)

## Security

- Router credentials are encrypted at rest using Fernet (AES)
- SSH key-based authentication is supported
- Audit logging for all changes

## Project Structure

```
router-mgmt/
├── backend/
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── core/         # Config, database, security
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   └── main.py      # FastAPI app
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/   # Vue components
│   │   ├── views/       # Page views
│   │   ├── stores/      # Pinia stores
│   │   ├── api/         # API client
│   │   └── types/       # TypeScript types
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── SPEC.md
└── README.md
```

## License

MIT
