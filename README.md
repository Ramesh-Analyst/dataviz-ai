# DataViz AI Platform 📊🤖

DataViz AI is a premium automated data analysis and visualization platform. It allows users to upload datasets (CSV, Excel), view instant data quality profiling metrics, interact with a smart custom chart builder, get AI-assisted recommendations, and ask natural language questions to generate instant chart visualizations and factual summaries.

Designed as an end-to-end recruiter showcase and technical portfolio item, this repository exhibits solid architectural patterns, strict ownership boundary isolations, robust query compilation validations, and high-performance interactive widgets.

---

## 🏗️ Core Architecture & Flow

The application follows a decoupled client-server architecture:

```
┌────────────────────────────────┐
│      React Client (Vite)       │
│  - HSL Harmonious Design Mode  │
│  - ECharts Dynamic Graphics    │
└──────────────┬─────────────────┘
               │ HTTPS JSON APIs / Auth Tokens
               ▼
┌────────────────────────────────┐
│      FastAPI App Backend       │
│  - Deterministic NL Parser     │
│  - Pandas Profile Engine       │
└──────────────┬─────────────────┘
               │ SQLite ORM (SQLAlchemy)
               ▼
┌────────────────────────────────┐
│   SQLite Database + Storage    │
│  - Cascading Foreign Keys      │
│  - Sandbox File Store uploads/ │
└────────────────────────────────┘
```

1. **Authentication Flow**: Structured with JSON Web Tokens (JWT) using OAuth2 password flow, `passlib` bcrypt hashing, and SQLite user storage. Tokens are handled with strict local session states.
2. **Dataset Ingestion & Storage**: Safe upload sandbox generating randomized UUID filenames to prevent path traversals and name collisions.
3. **Profiling & Quality Engine**: Computes dataset dimensions, null rates, IQR statistical outliers, constant columns, duplicate rows, and formats type conflicts. Compiles an itemized quality score from 0-100.
4. **Smart Visualizer & ECharts**: Resolves custom aggregations (Sum, Average, Min, Max, Median, Count) via Pandas. Employs strong input type-checking to block invalid requests (e.g. non-numeric axes in Scatter Plots) directly at the source.
5. **Ask Your Data (NL Engine)**: Translates user questions deterministically into a structured chart configuration and aggregation queries, which are then summarized factually using `pandas` calculations.

---

## 🛠️ Technology Stack

* **Frontend**: React 19, Vite, Tailwind CSS, Lucide icons, React Router v7, Apache ECharts.
* **Backend**: Python 3.13, FastAPI, SQLAlchemy, SQLite, Pandas, NumPy, Pydantic, Passlib, Python-Jose, Pytest.

---

## 🚀 Getting Started & Startup Instructions

### Prerequisites
* Python 3.12+ / 3.13 installed
* Node.js v18+ installed

### Step 1: Clone and Environment Setup
```bash
# Clone the repository
git clone https://github.com/your-username/dataviz-ai.git
cd dataviz-ai
```

### Step 2: Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv .venv
# Activate virtual environment
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env from template
copy .env.example .env  # Or copy manually
```

Configure your `.env` settings as needed. The database will automatically initialize SQLite schemas on first run.

### Step 3: Start Backend API Server
```bash
# From within the backend directory with active virtual environment:
uvicorn app.main:app --reload --port 8000
```
API docs will be available at `http://127.0.0.1:8000/docs`.

### Step 4: Frontend Setup
```bash
cd ../frontend

# Install node dependencies
npm install

# Run the client app locally
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🧪 Running Automated Tests

DataViz AI utilizes Pytest for testing backend APIs and services. The tests validate auth lifecycles, dataset profiling, quality calculations, chart validations, and database cascade deletion.

```bash
# From the root directory:
$env:PYTHONPATH="."; backend\.venv\Scripts\pytest

# From within the backend folder:
$env:PYTHONPATH=".."; .venv\Scripts\pytest
```

---

## 🔒 Security & Reliability Implementations

* **SQLite Cascading Ref-Integrity**: Explicitly configures connection-level listener `PRAGMA foreign_keys=ON` to enforce dashboard/widget cleanup when parent datasets are deleted.
* **Input Isolation & Safe Paths**: Restricts uploads by suffix validation, using unique GUID storage paths, preventing filename traversal leaks.
* **Granular Owner Verification**: Endpoints explicitly evaluate `models.Dataset.user_id == current_user.id` to prevent cross-tenant dataset reads, dashboard modifications, or widget queries.
* **Aesthetic Quality Bounds**: Data quality progress bar widths dynamically compute against individual metric ceilings (not hardcoded sizes), aligning frontend UI values with backend engines.
* **Incomplete State Protection**: The frontend chart builder validates configuration models locally prior to calling query APIs, resetting mismatched options on chart type switches, ensuring no query compiler errors appear for normal incomplete choices.

---

## ⚠️ Known Limitations

* **SQLite Concurrency**: Uses SQLite for simplicity in demonstrations. High-concurrency operations might cause table lockouts. For production staging, configure PostgreSQL by adapting the `DATABASE_URL` settings.
* **Query Limit Caps**: Dataset query results are capped at 1000 rows when aggregation is set to `none` to safeguard frontend memory against heavy datasets.
