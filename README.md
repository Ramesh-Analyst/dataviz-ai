# DataViz AI Platform 📊🤖

DataViz AI is a full-stack automated data analysis and visualization platform that transforms CSV and Excel datasets into interactive analytical workspaces. Users can upload datasets, inspect schema and data-quality metrics, build custom visualizations, ask natural-language analytical questions, and pin useful charts to persistent dashboards.

The platform combines a React-based analytical interface with a FastAPI backend, Pandas-powered profiling and aggregation, secure dataset ownership controls, and deterministic natural-language query interpretation.

---

## 🌐 Live Demo

Try the deployed application: https://dataviz-ai-1.onrender.com

---

## ✨ Key Features

* **Spreadsheet Ingestion**: Supports CSV, XLSX, and XLS file formats with automated file type and structure validation.
* **Schema Inference & Dataset Profiling**: Infers data types (Identifier, Categorical, Numeric, Date/time, Boolean, Geographic candidate) and calculates basic summary statistics.
* **Data Quality Scoring**: Generates an explainable quality score (0–100) based on automated audits of missing values, duplicates, constant columns, and statistical outliers.
* **Interactive Chart Builder**: Constructs visualizations (bar, line, scatter, pie, histogram) with aggregation functions (Sum, Average, Min, Max, Median, Count, None).
* **Natural-Language Analytical Queries**: Translates analytical questions into chart configurations and factual summaries powered by Pandas calculations.
* **Persistent Dashboards**: Allows users to save customized chart configurations as interactive dashboard widgets.
* **Statistical Insights**: Highlights correlations, distributions, skewness alerts, and key data takeaways.
* **User Authentication**: Secures workspaces via JWT-based OAuth2 authentication and enforces ownership-level isolation on dataset resources.

---

## 🏗️ Core Architecture & Flow

The application follows a decoupled client-server architecture:

```
┌────────────────────────────────┐
│      React Client (Vite)       │
│  - Modern Responsive Layout    │
│  - ECharts Dynamic Graphics    │
└──────────────┬─────────────────┘
               │ HTTPS JSON APIs / JWT Auth Tokens
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

1. **Authentication Flow**: Uses JSON Web Tokens (JWT) for secure authentication. The JWT is stored in `localStorage` on the client and sent in the `Authorization: Bearer <token>` header of HTTP requests. The backend validates tokens using FastAPI security dependencies.
2. **Dataset Ingestion & Storage**: Saves files in a dedicated storage directory generating randomized UUID filenames to prevent path traversal vulnerabilities.
3. **Profiling & Quality Engine**: Uses Pandas to calculate dataset shape, missing rates, duplicate counts, constant columns, and statistical outliers (via IQR).
4. **Validation Logic**: The backend validates chart configurations directly before execution:
   * Verifies that the requested axes and group-by fields exist in the dataset schema.
   * Restricts non-count aggregations to numeric Y-axis columns.
   * Enforces coordinate checks based on chart types (e.g., Pie chart requires a categorical/boolean/identifier X-axis, Scatter plot requires numeric X and Y axes, Histogram requires a numeric X-axis).
5. **Ask Your Data (NL Engine)**: Deterministically parses user queries into chart metrics, filters, and aggregations, computing results dynamically on the dataset via Pandas.

---

## 🛠️ Technology Stack

### Frontend
* **Core Framework**: React v19.2.7 (Vite v8.1.1)
* **Routing**: React Router DOM v7.18.1
* **Styling**: Tailwind CSS v3.4.17, Lucide Icons v1.23.0
* **API Client**: Axios v1.18.1
* **Charts**: Apache ECharts v6.1.0

### Backend
* **Core API Framework**: FastAPI v0.111.0 (Uvicorn v0.30.1)
* **Configuration & Validation**: Pydantic v2.7.4, Pydantic Settings v2.3.4, Python-Dotenv v1.0.1
* **Authentication**: Passlib v1.7.4 (Bcrypt), Python-Jose v3.3.0 (with Cryptography), Python-Multipart v0.0.9, Email-Validator v2.1.1

### Data Processing & Visualization
* **Computation Engine**: Pandas v3.0.3, NumPy v2.5.0, Openpyxl v3.1.5
* **React Chart Component**: ECharts for React v3.0.6

### Database and ORM
* **Database**: SQLite (local default)
* **ORM Layer**: SQLAlchemy v2.0.31
* **PostgreSQL Driver**: Psycopg2-Binary v2.9.12 (supported for production configuration)

### Testing
* **Test runner**: Pytest (FastAPI TestClient)

---

## 🔒 Security & Reliability

* **Database Cascading Integrity**: Enforces `PRAGMA foreign_keys=ON` on the SQLite connection to trigger automatic cascade deletions of associated charts and widgets when parent datasets are deleted.
* **Upload Sandbox Isolation**: Validates extensions (`.csv`, `.xlsx`, `.xls`), restricts file size to the configured limit, and maps uploads to randomized UUID paths to block filename traversal vulnerabilities.
* **Granular Owner Verification**: Route handlers check `models.Dataset.user_id == current_user.id` on data query and modification requests, ensuring users cannot access or edit other users' datasets.
* **Quality Metric Visualization**: Progress metrics and quality grades map directly to calculated backend data quality dimensions rather than relying on client-side hardcoding.
* **Pre-Query Frontend Validation**: Prevents chart builder API execution errors by validating configuration models locally and automatically resetting incompatible axes parameters on chart type switches.

---

## 🚀 Getting Started & Startup Instructions

### Prerequisites
* Python 3.12 or 3.13
* Node.js v18 or newer

### Step 1: Clone the Repository
```bash
git clone https://github.com/Ramesh-Analyst/dataviz-ai.git
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

# Create environment configuration
# On Windows PowerShell:
Copy-Item .env.example .env
# On macOS/Linux:
cp .env.example .env
```
Ensure you update `.env` variables if customization is required. SQLite schema tables will initialize automatically on server startup.

### Step 3: Start the Backend Server
From within the `backend` directory (with active virtual environment):
```bash
uvicorn app.main:app --reload --port 8000
```
Interactive Swagger API documentation will be available at `http://127.0.0.1:8000/docs`.

### Step 4: Frontend Setup
Open a new terminal window at the project root directory:
```bash
cd frontend

# Install node packages
npm install

# Start Vite development server
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🧪 Running Automated Tests

DataViz AI utilizes Pytest to validate backend APIs and core profiling/query services. The test suite covers:
* Authentication and registration onboarding lifecycles.
* Dataset spreadsheet parsing, profile extraction, and column type inference.
* Statistical outlier calculations, missingness rates, and correlation matrices.
* Chart coordinate schema validations and aggregation compatibility checks.
* Cascading database constraints and user ownership isolation logic.

#### Windows PowerShell (from root directory):
```powershell
$env:PYTHONPATH="."; backend\.venv\Scripts\pytest
```

#### Windows PowerShell (from backend directory):
```powershell
$env:PYTHONPATH=".."; .venv\Scripts\pytest
```

#### macOS/Linux (from root directory):
```bash
PYTHONPATH=. backend/.venv/bin/pytest
```

#### macOS/Linux (from backend directory):
```bash
PYTHONPATH=.. .venv/bin/pytest
```

---

## 📷 Screenshots & Application Flow

Follow the end-to-end user journey and interface flow of the DataViz AI platform:

### 1. Landing Page
![Landing Page](docs/screenshots/landing-page.png)
*The public landing page introducing the platform's automated schema profiling, data auditing, and interactive visualization features.*

### 2. Login Page
![Login Portal](docs/screenshots/login-page.png)
*The secure authentication portal for workspace access.*

### 3. User Workspace / Dataset Home
![Workspace Dashboard](docs/screenshots/home.png)
*The post-upload dashboard displaying inferred column metadata and summarizing dataset attributes.*

### 4. Dataset Upload
![Ingestion Workspace](docs/screenshots/upload-page.png)
*The dedicated drag-and-drop workspace supporting spreadsheet uploads up to 10MB.*

### 5. Upload Result / Initial Dataset Summary
![Metadata Profiling Summary](docs/screenshots/dataset-overview.png)
*The primary overview screen displaying row and column count metrics, storage size, and data quality grades alongside interactive column profile summaries.*

### 6. Dataset Overview and Profiling
![Inferred Schema and Preview](docs/screenshots/dataset-overview%201.png)
*Tabular grid view rendering the first 10 rows of the imported dataset for structure inspection.*

### 7. Detailed Distribution / Missing-Rate Analysis
![Attribute Profiling](docs/screenshots/dataset-overview%202.png)
*Detailed visual statistics showing missingness rates per column and a Pearson correlation heatmap.*

### 8. Data Quality Audit
![Data Quality Audit Tab](docs/screenshots/data-quality.png)
*Explainable data quality scorecard from 0-100 detailing duplicate entries, missing elements, outliers, and automated cleanup advice.*

### 9. Smart Visualizations
![Smart Visualization Tool](docs/screenshots/smart-visualizations.png)
*Visual chart builder configuring columns, chart type, and aggregation controls with real-time rendering.*

### 10. Ask Your Data
![Natural Language AI Chat](docs/screenshots/ask-your-data.png)
*Natural language query interface producing automatic chart rendering and factual summary explanations.*

### 11. Interactive Dashboard
![Interactive Dashboard View](docs/screenshots/interactive-dashboard.png)
*A persistent dashboard layout consolidating pinned widgets (bar, line, scatter charts) with global filters and responsive arrangements.*

### 12. Statistical Narrative Insights
![Statistical Insights narrative](docs/screenshots/statistical-insights.png)
*An automated analytical narrative reporting skewness observations and correlation highlights.*

---

## ⚠️ Known Limitations

* **SQLite Concurrency**: SQLite is utilized for simplicity in local setups. Concurrent writes may trigger SQLite database locks. For staging or production use, a PostgreSQL database should be configured using the `DATABASE_URL` environment variable.
* **Aggregation Plot Capping**: Visual query executions are limited to a maximum of 1,000 data rows when aggregation is set to `none` to preserve client-side rendering performance.

---

## 🔮 Future Improvements

* **Object Storage Ingestion**: Abstracting cloud storage modules (e.g., AWS S3) for uploaded datasets rather than relying on local uploads directory writes.
* **Docker Containerization**: Provisioning container scripts (`Dockerfile`, `docker-compose.yml`) for instant application deployment.
* **CI/CD Integration**: Creating automated GitHub Actions pipelines to run test suites and frontend builds on pull requests.
