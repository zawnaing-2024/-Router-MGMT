# Router Automation & Management Portal - SPEC.md

## 1. Concept & Vision

A professional network operations center (NOC) dashboard for network engineers to manage multi-vendor routers. Clean, data-dense interface that prioritizes operational efficiency over flashy visuals. Feels like enterprise network management software but with modern UX patterns.

## 2. Design Language

**Aesthetic:** Dark mode NOC dashboard with high-contrast data visualization. Inspired by Datadog/Grafana but cleaner.

**Color Palette:**
- Background: `#0f172a` (slate-900)
- Surface: `#1e293b` (slate-800)
- Border: `#334155` (slate-700)
- Primary: `#3b82f6` (blue-500)
- Success: `#22c55e` (green-500)
- Warning: `#f59e0b` (amber-500)
- Danger: `#ef4444` (red-500)
- Text Primary: `#f1f5f9` (slate-100)
- Text Secondary: `#94a3b8` (slate-400)

**Typography:**
- Font: `Inter` for UI, `JetBrains Mono` for configs/CLI
- Headings: 600 weight
- Body: 400 weight
- Monospace: 400 weight

**Spacing:** 4px base unit. Consistent 16px/24px padding for cards/containers.

**Motion:** Minimal. 150ms transitions for hover states. No decorative animations.

## 3. Layout & Structure

**Sidebar Navigation (240px):**
- Logo/Brand
- Dashboard
- Routers (inventory)
- Configs (backup list)
- Templates
- Jobs (scheduled tasks)
- Terminal (live SSH)
- Settings

**Main Content Area:**
- Header with breadcrumb + actions
- Content area with responsive grid
- Cards for data groupings

**Responsive:** Desktop-first (1280px+). Tablet (768px+) collapses sidebar to icons. Mobile (640px) shows hamburger menu.

## 4. Features & Interactions

### 4.1 Router Inventory
- List all routers with status indicators (online/offline/warning)
- Add/edit router: hostname, IP, vendor, credentials (encrypted)
- Filter by vendor, status, location
- Bulk actions: backup now, run command
- Click row to expand details panel

### 4.2 Config Backup & Restore
- View backup history per router
- One-click backup
- Schedule automated backups (cron-like)
- Compare configs (diff view)
- One-click restore to router
- Version history with timestamps

### 4.3 Config Templates
- Create/edit configuration templates with variables
- Jinja2 syntax support
- Assign templates to router groups
- Preview rendered config
- One-click apply to router

### 4.4 Live Terminal
- Browser-based SSH terminal
- Connect to any managed router
- Command history
- Copy/paste support
- Session logging

### 4.5 Jobs & Scheduling
- Create backup schedules
- View job history and status
- Enable/disable jobs
- Email notifications on failure

### 4.6 Dashboard
- Router status overview (pie chart)
- Recent backups timeline
- Failed jobs alerts
- Quick actions panel

## 5. Component Inventory

### Navigation
- `Sidebar` - Fixed left, collapsible, active state highlight
- `TopBar` - Breadcrumb, search, user menu

### Data Display
- `DataTable` - Sortable, filterable, pagination, row actions
- `StatusBadge` - Online/Offline/Warning states
- `DiffViewer` - Side-by-side or unified diff
- `Terminal` - xterm.js integration
- `StatCard` - Metric with trend indicator

### Forms
- `RouterForm` - Add/edit router modal
- `TemplateEditor` - Code editor with syntax highlighting
- `ScheduleForm` - Cron-style scheduling UI

### Feedback
- `Toast` - Success/error notifications
- `ConfirmDialog` - Destructive action confirmation
- `LoadingSpinner` - For async operations

## 6. Technical Approach

### Frontend
- **Framework:** Vue 3 (Composition API)
- **Build:** Vite
- **State:** Pinia
- **Router:** Vue Router 4
- **Styling:** Tailwind CSS
- **Icons:** Lucide Vue
- **Terminal:** xterm.js + websocket
- **Code Editor:** Monaco Editor (for configs)

### Backend
- **Framework:** FastAPI
- **Language:** Python 3.11+
- **ORM:** SQLAlchemy 2.0
- **Database:** MySQL 8.0
- **SSH:** Paramiko
- **Task Queue:** Celery + Redis (for scheduled jobs)
- **WebSocket:** for live terminal

### API Design

```
GET    /api/routers                 - List routers
POST   /api/routers                 - Add router
GET    /api/routers/{id}            - Get router details
PUT    /api/routers/{id}            - Update router
DELETE /api/routers/{id}            - Delete router
POST   /api/routers/{id}/backup     - Trigger backup
POST   /api/routers/{id}/connect    - Test connection

GET    /api/backups                 - List all backups
GET    /api/backups/{id}            - Get backup content
POST   /api/backups/{id}/restore    - Restore backup
DELETE /api/backups/{id}            - Delete backup

GET    /api/templates               - List templates
POST   /api/templates               - Create template
PUT    /api/templates/{id}          - Update template
DELETE /api/templates/{id}          - Delete template
POST   /api/templates/{id}/render   - Render with vars

GET    /api/jobs                    - List scheduled jobs
POST   /api/jobs                    - Create job
PUT    /api/jobs/{id}               - Update job
DELETE /api/jobs/{id}               - Delete job

WS     /ws/terminal/{router_id}     - Live terminal connection
```

### Data Model

```
Router
├── id, hostname, ip_address, port
├── vendor (cisco/juniper/mikrotik/etc)
├── credentials (encrypted)
├── location, tags
├── status, last_seen
└── created_at, updated_at

ConfigBackup
├── id, router_id
├── content, checksum
├── timestamp
└── created_by (manual/scheduled)

ConfigTemplate
├── id, name, vendor
├── content (jinja2)
├── variables (json schema)
└── created_at, updated_at

ScheduledJob
├── id, name, type (backup/command/template)
├── router_ids or group
├── schedule (cron expression)
├── enabled, last_run, next_run
└── created_at, updated_at
```

### Security
- Router credentials encrypted at rest (Fernet/AES)
- SSH key-based auth preferred
- Audit logging for all changes
- Role-based access (future)

## 7. Project Structure

```
router-mgmt/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   ├── stores/
│   │   ├── composables/
│   │   └── App.vue
│   ├── package.json
│   └── vite.config.ts
└── docker-compose.yml
```
