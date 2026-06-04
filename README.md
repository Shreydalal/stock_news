# Market Intelligence Bot

An automated, production-ready daily market intelligence system written in Python 3.12 with FastAPI, SQLAlchemy, PostgreSQL (Supabase), and Groq AI. 

The bot automatically fetches financial data, computes technical indicators, generates AI-powered intelligence reports in Markdown, registers database indexes, pushes updates directly to a GitHub repository to maintain daily contribution streaks, and dispatches multi-channel alerts (Telegram notifications & PDF email attachments).

---

## 📈 Architecture & System Flow

The system is designed using **Clean Architecture** principles:
- **API Layer**: Exposes FastAPI endpoints for health checks, data inspection, charting data, and manual pipeline triggers.
- **Service Layer**: Houses core business logic (yfinance integration, Pandas indicator vector math, Groq AI text composition, subprocess Git operations, ReportLab PDF formatting, SMTP mail engines).
- **Repository Layer**: Provides database queries on top of SQLAlchemy models for clean encapsulation.
- **Scheduler**: Employs `APScheduler` to run daily, weekly, and monthly collection routines.

```mermaid
flowchart TD
    subgraph Core App Context
        Scheduler[APScheduler Cron] -->|Trigger Daily 7PM IST| Pipeline[Daily Pipeline Orchestrator]
        API[FastAPI Endpoints] -->|Manual POST Trigger| Pipeline
        
        Pipeline -->|1. Fetch Tickers| MDService[Market Data Service]
        MDService -->|yfinance API| YahooFinance[(Yahoo Finance)]
        MDService -->|Store OHLCV| DB[(Supabase/PostgreSQL)]
        
        Pipeline -->|2. Compute Math| IndService[Indicator Service]
        IndService -->|Calculate SMA, RSI, MACD, BB| DB
        
        Pipeline -->|3. Compile Text| AIService[AI Report Service]
        AIService -->|Prompts Llama-3-70b| GroqAPI(Groq LLM API)
        
        Pipeline -->|4. Persist & Deploy| GitService[Git Automation Service]
        GitService -->|Write File| LocalDisk[reports/YYYY/MM/DD/report.md]
        GitService -->|subprocess git commit & push| GitHub[(GitHub Remote Repository)]
        
        Pipeline -->|5. Multi-Channel Alerts| AlertService[Alert & Notification Service]
        AlertService -->|httpx POST| Telegram[Telegram Bot Channel]
        AlertService -->|SMTP Attachment| Email[User Email SMTP Server]
    end
```

---

## 🚀 Key Features

1. **Automatic Market Ingestion**: Tracks NIFTY 50 (`^NSEI`), BANKNIFTY (`^NSEBANK`), SENSEX (`^BSESN`), Gold (`GC=F`), Silver (`SI=F`), Bitcoin (`BTC-USD`), and Ethereum (`ETH-USD`).
2. **Indicators Calculated**:
   - **Moving Averages**: SMA 20, 50, 200
   - **Momentum**: RSI 14 (Wilder's smoothed)
   - **Trend**: MACD line (EMA 12 - EMA 26)
   - **Volatility**: Bollinger Bands (Upper, Lower 2.0 Std Dev)
   - **Support & Resistance**: Last 30-day absolute Lows & Highs
3. **Structured AI Reports**: Sections include Executive Summary, Asset breakdowns, Risk Factors, Trading Opportunities, and Tomorrow Outlook.
4. **Git Automation**: Writes reports to disk and runs Git subprocesses (`add`, `commit`, `push`) automatically using the `GITHUB_TOKEN`.
5. **Flexible Database Adaptor**: Connects to Supabase (PostgreSQL) in production, but automatically falls back to an out-of-the-box local `test.db` SQLite schema if no URL is provided.
6. **Robust Notification Alerting (Bonus)**:
   - **Telegram Channel alerts** summarizing closing values.
   - **Styled PDF compiles** attached to SMTP emails using ReportLab.
   - **Dashboard chart endpoints** returning synchronized dates, prices, and indicator array streams.
   - **Weekly & Monthly review** summaries.

---

## 🛠️ Configuration & Secrets

The application is configured using Pydantic Settings. You can create a `.env` file in the root directory:

```env
# Database Configuration
DATABASE_URL=postgresql://user:password@hostname:5432/dbname # Falls back to local SQLite if empty

# External APIs
GROQ_API_KEY=your_groq_api_key_here # Uses fallback mock generator if empty
ALPHA_VANTAGE_KEY=optional_key

# Git Push Integration
GITHUB_TOKEN=your_github_token_here
GITHUB_REPOSITORY=username/repo-name

# Telegram Webhook Alerts
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# SMTP Email Setup
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=sender@gmail.com
SMTP_PASSWORD=gmail_app_password
EMAIL_TO=recipient@domain.com
```

---

## 💻 Local Setup & Execution

### 1. Bare Metal Setup
1. **Clone repository & enter directory**:
   ```bash
   git clone <repo-url>
   cd market-intelligence-bot
   ```
2. **Install Python 3.12 dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the FastAPI development server**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
4. Access Swagger documentation at: [http://localhost:8000/docs](http://localhost:8000/docs).

### 2. Docker Compose Setup
Run the application alongside a local PostgreSQL instance:
```bash
docker-compose up --build
```

---

## 🧪 Testing

The project uses `pytest` for unit and integration testing. Mocks are in place to intercept outbound calls to Yahoo Finance, Groq, SMTP, and Git.

To execute tests and measure coverage:
```bash
pytest -v --cov=app
```

---

## 📡 API Documentation

### System
- `GET /health`: Inspects database connectivity and APScheduler running status.

### Market Data
- `GET /assets`: Lists symbols currently being tracked.
- `GET /market-data`: Returns raw historical OHLCV data. Filterable by `symbol` and `limit`.
- `GET /market-data/latest`: Returns latest closing values collated with computed SMAs, RSI, Bollinger Bands, and Support/Resistance for all assets.
- `GET /market-data/charts`: Returns chart-ready JSON history for plotting (aligned arrays of prices, SMAs, Bollinger Bands, and RSI).
- `POST /fetch-market-data`: Manually triggers yfinance collection and calculations. Supports `force_backfill=True` parameter.

### Reports
- `GET /reports`: Lists indexed daily reports.
- `GET /reports/latest`: Retrieves the latest generated report text.
- `GET /reports/{date}`: Retrieves a report by specific calendar date (e.g. `2026-08-15`), reading the Markdown from disk.
- `POST /generate-report`: Manually triggers AI compilation, disk persistence, Git pushes, and communications. Accepts `report_type` (`daily`, `weekly`, `monthly`).

---

## ☁️ Deployment Guide (Render / Railway)

### 1. Supabase setup
1. Create a free Supabase project.
2. Grab the connection string from Database Settings (Connection Pooling mode is recommended, e.g., port 6543).

### 2. Render Web Service Deployment
1. Connect your GitHub repository.
2. Choose **Web Service** or **Background Worker**.
3. Choose Environment: **Python3** or **Docker**. (Using Docker utilizes our optimized multi-stage `Dockerfile`).
4. Set the Build Command (if using Python runner):
   ```bash
   pip install -r requirements.txt
   ```
5. Set Start Command:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
6. Add the environment variables from the `.env` section in the **Environment** tab on Render.

---

## 🔮 Future Improvements
- Add Interactive frontend UI dashboards using React/Tailwind to plot the `/market-data/charts` payload.
- Integrate Sentiment Analysis from financial news APIs (e.g., Bloomberg/Reddit) as additional LLM prompt inputs.
- Incorporate a paper-trading execution model based on identified trading opportunities.
