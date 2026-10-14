<div align="center">

# Smart Quotation System

**Catalog management · Natural-language search · Bundle quotation** — a self-hosted tool

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![Node](https://img.shields.io/badge/Node.js-18%2B-339933?logo=nodedotjs&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi&logoColor=white)
![Database](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)

[中文](README.md)　·　**English**

License: (TBD: LICENSE)　·　Version: 1.0.0

</div>

---

## 📖 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Screenshots](#-screenshots)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [API Overview](#-api-overview)
- [Project Structure](#-project-structure)
- [Production Deployment](#-production-deployment)
- [Data & Backup](#-data--backup)
- [Security & Privacy](#-security--privacy)
- [FAQ](#-faq)
- [Contributing](#-contributing)
- [License](#-license)
- [Contact](#-contact)

> 中文说明：[README.md](README.md)

---

## 🧭 Overview

Smart Quotation System is a **self-hosted** product catalog and quotation tool. It consolidates product data that usually lives in scattered spreadsheets, lets you look items up quickly with natural language or dropdown filters, and automatically builds multiple workable quotation bundles under constraints such as total price, category mix, and per-item price/discount limits.

The system consists of two parts that communicate over HTTP/JSON:

- **frontend/** — the browser UI (React + TypeScript single-page app)
- **backend/** — the API and business logic (FastAPI + SQLite)

All data is stored in a single local SQLite file; no external database or cloud service is required. AI features are **optional** and use the DeepSeek API key supplied by each user — every non-AI feature works without one.

> Scope note: this is a general-purpose quotation/bundling tool. The code base contains no business data, and the repository ships **no sample product data** — import your own.

---

## ✨ Features

| Capability | Description |
| --- | --- |
| Catalog management | Create/read/update/delete products, batch delete, pagination, header filters, link columns, table zoom, customizable column display (order / width / header label) |
| Batch Excel import | `.xlsx` / `.xls` / `.csv`, multiple files at once; fuzzy matching between spreadsheet headers and system fields, with manual column-mapping adjustment; duplicate strategies "skip / overwrite / error", plus per-row success, skip and failure details |
| Data export | Catalog, query results and bundle export, all as `.xlsx`; images are written as **in-cell pictures** (they move and resize with the cell instead of floating above the sheet) |
| Rule-based smart search | Parses free text into structured conditions: barcode, model, brand, category, price ranges, discount rate, sorting, fuzzy search |
| Batch model lookup | Submit many model numbers at once (one per line); results are grouped per model and can be exported |
| AI smart search | Sends natural language to DeepSeek and converts it into a query intent (e.g. "Philips power banks between 300 and 500 dropship price"), showing the token usage of each call |
| Bundle quotation | Enumerates feasible combinations under total price, overall discount, per-category quantity and price limits, ranked by closeness to the target; supports "any category" slots sampled across the whole catalog |
| No-solution diagnostics | When nothing matches, explains each cause (total price too high/low, discount out of range, price band too narrow, category empty) with suggestions computed from real data, plus one-click apply |
| Bundle management | Save bundles, review/reuse/delete history, export to Excel, and see bundles recommended by parent organizations |
| Multi-tenant isolation | Business data is isolated per company (organization); catalogs, bundles and users are invisible across organizations. An organization is identified by organization name + organization database password |
| Three roles + invite codes | Super admin > admin > user; invite codes are single-use, with configurable validity, renewal and deletion (deleting a used code cascades to that account and its data) |
| Guest mode | One-click guest entry from the login page, backed by a separate temporary organization; cleaned up on sign-out, session capped at 24 hours |
| Automatic cleanup | Periodic cleanup of expired upload caches; automatic removal of empty organizations that have no registered accounts |
| Themes | Light/dark theme toggle with persistence, available on the login page too |

---

## 🛠 Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend framework | React 18 + TypeScript 5 |
| Frontend build | Vite 5 |
| UI components | Ant Design 5 + custom CSS (light/dark themes) |
| Routing & state | React Router 6 + React Context |
| HTTP client | axios |
| Spreadsheet I/O (frontend) | xlsx |
| Backend framework | FastAPI + uvicorn |
| ORM / database | SQLAlchemy 2 (async) + aiosqlite → single SQLite file |
| Validation | Pydantic v2 |
| Spreadsheet processing | pandas + openpyxl + lxml + Pillow |
| Auth & crypto | PyJWT (HS256) + passlib/bcrypt (password hashing) + cryptography (encrypted sensitive fields) |
| AI (optional) | DeepSeek Chat API (via httpx) |
| Deployment example | Nginx + systemd |

Exact dependency versions are listed in `backend/requirements.txt` and `frontend/package.json`.

---

## 🖼 Screenshots

(TBD: screenshots. Suggested location `docs/screenshots/` or `assets/`, inserted here as `![Smart search page](path)`.)

---

## 🚀 Quick Start

### Requirements

| Dependency | Version | Notes |
| --- | --- | --- |
| Python | 3.9+ | Backend runtime (required by pinned dependencies, see `backend/requirements.txt`) |
| Node.js | 18+ (LTS) | Frontend development and build |
| PowerShell | Windows PowerShell 5.1+ | Needed only by the one-click `启动.bat` launcher (bundled with Windows 10+) |

> The one-click launcher is Windows-only; use the manual steps below on macOS / Linux.

### Option 1: Windows one-click launcher

1. Make sure Python and Node.js are installed and available on `PATH`
2. Double-click **`启动.bat`** in the project root
3. The script will: detect Python/Node → create or repair `.venv` → install backend dependencies (`pip install -r backend/requirements.txt`) → install frontend dependencies (`npm install`) → start the backend on port 8000 → wait for its health check → start the Vite dev server on port 5173 → open the browser
4. You land on the login page; on a fresh instance continue with "First-time setup" below

> Two console windows stay open (backend and frontend) — **closing them stops the service**. The first run is slower because dependencies are installed.

### Option 2: Manual start (cross-platform)

Backend (from the `backend/` directory, using an environment with the dependencies installed):

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend (separate terminal, from the `frontend/` directory):

```bash
cd frontend
npm install    # first run, or when dependencies change
npm run dev    # opens http://localhost:5173
```

- In development, Vite proxies `/api` to `http://127.0.0.1:8000` (see `frontend/vite.config.ts`)
- API docs (Swagger UI): <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/api/health>

### Production build (single-port hosting)

```bash
cd frontend
npm run build
```

On startup the backend checks whether `frontend/dist` exists; if it does, it serves that build directly, so a single port can host both the UI and the API.

### First-time setup

The first startup creates the database, the tables, and a **super-admin account together with the organization it belongs to**. These initial values live in the `SUPER_ADMIN_*` constants of `backend/app/config.py`:

> ⚠️ **Change them before deploying**: `SUPER_ADMIN_USERNAME`, `SUPER_ADMIN_PASSWORD`, `SUPER_ADMIN_COMPANY`, etc. (or refactor them to be read from environment variables). The defaults in the repository are meant for local trial runs only.

After initialization:

1. Sign in with the super-admin account
2. Create **invite codes** on the "User Management" page (first-level code → admin; second-level code → regular user)
3. Hand the code to the person who should register; they sign up from the login page with username, password, e-mail and the code
4. After signing up they join an existing organization (organization name + organization database password) or create a new one

---

## ⚙️ Configuration

All configuration lives in `backend/app/config.py` and every entry can be overridden by an environment variable.

| Environment variable | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite+aiosqlite:///<project>/data/data.db` | Async database URL |
| `SYNC_DATABASE_URL` | `sqlite:///<project>/data/data.db` | Sync database URL (table creation, migrations, seed data) |
| `HOST` | `0.0.0.0` | Backend bind address |
| `PORT` | `8000` | Backend port |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed frontend origins, comma-separated |
| `JWT_SECRET_KEY` | fixed development-only default | JWT signing key, **also used to derive the encryption key for sensitive fields (usernames, API keys)**. Must be a random value in production |
| `ADMIN_API_KEY` | empty | If set, written to the super admin's DeepSeek API key on first startup (**read from the environment, never hardcoded**) |
| `DEEPSEEK_API_URL` | `https://api.deepseek.com/v1/chat/completions` | AI endpoint |
| `DEEPSEEK_MODEL` | `deepseek-chat` | AI model name |

Other runtime constants (also in `config.py`):

| Constant | Value | Description |
| --- | --- | --- |
| `DATA_DIR` | `<project root>/data` | Runtime data directory (database, upload cache, export cache) |
| `UPLOAD_DIR` / `OUTPUT_DIR` | `data/uploads` / `data/output` | Upload staging and export output; created automatically when missing |
| `MAX_UPLOAD_SIZE` | 50 MB | Per-file upload limit (enforced by the backend; set the reverse proxy `client_max_body_size` to at least the same value) |
| `ALLOWED_EXTENSIONS` | `.xlsx` `.xls` `.csv` | Accepted import file types |
| `JWT_ALGORITHM` / `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `HS256` / 1440 | Token algorithm and lifetime (24 hours) |

> Example environment setup (illustrative only — never commit real secrets):
>
> ```bash
> export JWT_SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')"
> export CORS_ORIGINS="https://your-domain.example"
> export ADMIN_API_KEY="<your DeepSeek API key>"
> ```

---

## 📘 Usage

### Core workflow

**Import → Search → Build a bundle → Export.**

1. **Import**: open "Data Import", pick one or more Excel/CSV files, review the column mapping and duplicate strategy for each file, then confirm. The required fields are "quick-lookup model" and "dropship price" (the price may be 0 but not negative); "model" and "barcode" are optional.
2. **Smart search**: the search page supports three modes — type free text and press Enter, use the dropdown filters (conditions are combined with AND), or switch on the AI toggle and describe what you want. Results can be sorted, previewed with thumbnails, exported, or added to the bundle cart.
3. **Bundle quotation**: fill in total price / discount / per-category quantity and limits block by block, or paste a free-text requirement and let the AI parse it. The system enumerates feasible combinations and ranks them; bundles can be saved to history or exported to Excel. When nothing is feasible, a diagnostics panel proposes concrete adjustments that can be applied with one click.
4. **Export**: three entry points produce `.xlsx` — catalog, query results, bundle details.

### Roles and organization isolation

| Role | Created by | Capabilities |
| --- | --- | --- |
| Super admin | Automatically created on first startup | Full access; can issue first-level invite codes; can change any organization's database password |
| Admin | Invited by a super admin with a first-level code | Manages its own organization's catalog and data; can issue second-level codes |
| User | Invited by an admin with a second-level code | Search, bundles and data management; cannot issue invite codes |
| Guest | One click on the login page | Core features for evaluation; no user management; data removed on sign-out |

- An organization is identified by **organization name + organization database password**; the binding cannot be changed later, and a forgotten password must be reset by a super admin.
- Lower-privilege accounts additionally see products and bundles recommended by **organizations higher up the invite chain** (the source organization is labelled). They are references only — purchasing is arranged with the source organization directly.

### AI features (optional)

- Each user configures their own DeepSeek API key under the user menu → "API Key configuration"; the key is stored **encrypted** in the database.
- Every AI call reports the tokens it consumed, and the dialog shows cumulative usage.
- Everything except AI is free to use; AI calls are billed by DeepSeek according to your own key. See the [DeepSeek documentation](https://api-docs.deepseek.com/zh-cn/quick_start/pricing) for current pricing.

### Guest mode

Each guest gets a separate temporary organization whose data is invisible to everyone else. Signing out clears that session's data; if the browser is simply closed, the backend cleans it up after the session expires (24 hours).

---

## 🔌 API Overview

The backend exposes a REST API through FastAPI. Swagger UI is available at `/docs` and the OpenAPI document at `/openapi.json`. Routes are grouped by domain (`backend/app/routers/`):

| Prefix | Responsibility |
| --- | --- |
| `/api/auth` | Registration, login, current user, organization details, password change, personal API key configuration/status, guest login and guest cleanup |
| `/api/company` | Bind an organization (join or create), change the organization database password, clean up empty organizations |
| `/api/invites` | Create, list, verify, renew and delete invite codes (with cascading cleanup) |
| `/api/products` | Paginated/filtered catalog, product details, create/update/delete, batch delete, export, category/brand/filter options, recommended products |
| `/api/query` | Rule-based search, AI search, batch model lookup, query-result export |
| `/api/solution` | Analyze and generate bundles, save, export, history, recommended bundles |
| `/api/import` | Upload and parse a file (returns preview and column mapping), confirm the import |
| `/api/column-display` | Read and save column-display configuration, list available columns |
| `/api/health` (GET), `/api/cleanup` (POST) | Health check, manual cleanup trigger |

Apart from the public endpoints (registration, login, guest), requests must carry `Authorization: Bearer <token>`.

---

## 📁 Project Structure

```text
smart-quotation/
├── 启动.bat                     # Windows one-click launcher (delegates to launcher.ps1)
├── launcher.ps1                 # Launcher: environment checks, .venv create/repair, installs deps, starts both apps, opens browser
├── README.md                    # Chinese documentation
├── README.en.md                 # English documentation (this file)
├── backend/
│   ├── requirements.txt         # Python dependencies
│   └── app/
│       ├── main.py              # App entry: CORS, router registration, startup init, scheduled cleanup, serves frontend/dist
│       ├── config.py            # Central configuration (data dir, ports, upload limits, JWT, AI endpoint, initial admin)
│       ├── database.py          # Engine/session, table creation and migrations, seed data
│       ├── models.py            # ORM models (users, organizations, invite codes, products, column config, import templates/logs, bundles and items)
│       ├── schemas.py           # Pydantic request/response models
│       ├── routers/             # HTTP layer (routing, auth checks, parameter validation)
│       ├── services/            # Business layer: query engine, bundle engine, import/export, AI calls, cleanup
│       └── utils/               # Auth, crypto and Excel helpers
├── frontend/
│   ├── index.html               # HTML template (restores the saved theme before first paint)
│   ├── vite.config.ts           # Vite config: dev port 5173, /api proxied to 127.0.0.1:8000
│   └── src/
│       ├── pages/               # Page components (login, register, organization setup, search, data management, bundles, user management, 404)
│       ├── components/          # Reusable components (layout, tables, forms, import wizard, column config, ...)
│       ├── services/api.ts      # Single axios wrapper (token injection, 401 logout, error messages)
│       ├── store/               # Global state (auth, theme, page state)
│       └── types/               # TypeScript types
├── deploy/                      # Production deployment examples (see below)
├── data/                        # Runtime data (git-ignored, recreated automatically)
└── .gitignore
```

`data/`, `.venv/`, `node_modules/`, `frontend/dist/`, `__pycache__/` and `*.tsbuildinfo` are generated artifacts or local data and are not tracked.

---

## 🚢 Production Deployment

The `deploy/` directory contains an Nginx + systemd example for Ubuntu:

| File | Purpose |
| --- | --- |
| `deploy/deploy.sh` | One-shot deployment: install dependencies, build the frontend, configure Nginx and systemd, open the port |
| `deploy/nginx.conf` | Site template: reverse-proxies the public port to the backend (127.0.0.1:8008 by default) and relaxes body size and timeouts |
| `deploy/smart-quotation.service` | systemd unit: start on boot, restart on failure |
| `deploy/update.sh` | Update script: fix permissions → rebuild frontend → restart backend |

Adjust the placeholders (domain, port, install path) to your own environment before using them; the scripts contain values you are expected to replace. Also note:

- `JWT_SECRET_KEY` must be set to a random value (see [Security & Privacy](#-security--privacy))
- Change the `SUPER_ADMIN_*` initial administrator values
- Keep the reverse proxy `client_max_body_size` in line with the backend `MAX_UPLOAD_SIZE`
- Always enable HTTPS when exposing the service publicly

> These templates are examples and have not been verified on every distribution or environment — review them before going live.

---

## 💾 Data & Backup

- All business data lives in **`data/data.db`** (a single SQLite file): products, users, organizations, invite codes, bundles, column configuration, import logs.
- Backing up means copying that file; restoring means putting the backup back in place.
- `data/uploads/` (upload staging) and `data/output/` (export cache) can be deleted at any time — they are recreated and are cleaned periodically in the background.
- Deleting the whole `data/` directory **erases all business data**: on the next start the database is rebuilt empty and the initial administrator is seeded again.

```bash
# Backup example (stop the service first so the file is consistent)
tar -czf data-backup-$(date +%Y%m%d).tar.gz data
```

---

## 🔒 Security & Privacy

- **No secrets are bundled.** AI capability uses each user's own DeepSeek API key, stored encrypted and never written to plain-text logs.
- **`JWT_SECRET_KEY` must be set to a random value in production.** It signs login tokens and also derives the encryption key for sensitive fields; keeping the default makes tokens forgeable and stored keys decryptable.
- **Change the initial administrator account and organization** (the `SUPER_ADMIN_*` constants in `config.py`) — do not reuse the values shipped in the code.
- Passwords are hashed with bcrypt; sensitive fields such as usernames are encrypted and additionally hashed with HMAC to allow equality lookups.
- Multi-tenant isolation: every read and write is scoped to an organization, so organizations cannot see each other's data.
- Never commit `.env` files, key files, the `data/` directory, or any spreadsheet containing real data; consider adding a secret scanner (e.g. gitleaks) to the contribution workflow.
- For public deployments: enable HTTPS, restrict access to administrative endpoints, back up regularly and rotate keys.
- The system processes product and pricing data — make sure the data you import is lawfully obtained and licensed for your use.

---

## ❓ FAQ

**The page does not open / "This site can't be reached"**
The service is probably not running. Start it again with `启动.bat` (or start both apps manually) and confirm both processes are alive.

**"Company name or company database password is incorrect"**
Check the organization name matches exactly what your administrator gave you (including spaces and casing) and that the organization database password is correct; if it is lost, a super admin has to reset it.

**"Account expired, login disabled"**
The account's validity period has ended — ask an administrator to renew it on the "User Management" page.

**The launcher window closed after an error**
Make sure Python 3.9+ and Node.js 18+ are installed and on `PATH`. You can also run `launcher.ps1` directly from PowerShell to see the full log.

**The search returns nothing**
The filters may be too strict (remove some first); check that the catalog actually contains data; or try a natural-language search.

**Imported data is scrambled or the import fails entirely**
Verify the column mapping of your spreadsheet. The required fields are "quick-lookup model" and "dropship price". Read the per-row error messages in the import result, fix the file and retry.

**Upload/import errors (timeout, file too large, ...)**
The UI reports descriptive errors. The per-file limit is controlled by `MAX_UPLOAD_SIZE` in `config.py` (50 MB by default); the reverse proxy must allow the same or a larger body size and a longer timeout. Large-file failures can also be caused by slow upstream bandwidth — try importing in batches.

**AI features fail or cannot be enabled**
Check that a valid DeepSeek API key is configured in the user menu. For 500-class errors, restart the backend to make sure the latest code is running.

**I lost my data**
Check whether `data/data.db` still exists. If the file is gone and you have no backup, the data cannot be recovered — please back it up regularly.

**Is guest data kept?**
No. It is removed on sign-out, and the backend also cleans it up once the session expires (24 hours) even if the browser was closed.

**Users of an organization were all deleted — is its data still there?**
No leftovers. On startup and through the background task, the system removes any organization that has no registered accounts, together with its data.

---

## 🤝 Contributing

Issues and pull requests are welcome.

(TBD: `CONTRIBUTING.md` — development requirements, coding style, commit message conventions, branch/PR workflow, test and lint commands.)

Before submitting, please make sure your change contains no real secrets or personal data, follows the existing code style, and keeps both README files (Chinese and English) in sync when documentation is affected.

---

## 📄 License

(TBD: no license file yet. Add a `LICENSE` file at the repository root and state the license here — for example MIT or Apache-2.0 — before publishing. Until a license is chosen, all rights are reserved.)

---

## 📮 Contact

- Bug reports and feature requests: please open a GitHub Issue in this repository
- Repository: <https://github.com/emendator/Quote>
- Maintainer and e-mail: (TBD: maintainer name / e-mail)

---

<div align="center">

A self-hosted tool for catalog management and quotation workflows · [中文](README.md)

</div>
