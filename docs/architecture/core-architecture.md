# Core Architecture Diagrams

---

## 1. System Architecture (High-Level Overview)

The entire system from user to outputs, showing all departments and their relationship to external services.

```mermaid
graph TB
    USER["<b>Board of Directors</b><br/>(You)"]

    subgraph Executive["Executive Layer"]
        CIO["<b>exec-cio</b><br/>Chief Investment Officer<br/><i>opus</i>"]
        COO["<b>exec-coo</b><br/>Chief Operations Officer<br/><i>haiku</i>"]
    end

    subgraph FrontOffice["Front Office"]
        subgraph TradingDesk["Trading Desk"]
            DDM["<b>Drawdown Monitor</b>"]
            MKT["<b>Market Analyst</b>"]
            SWS["<b>Swing Screener</b>"]
        end
        subgraph ResearchDiv["Research Division"]
            MACRO["<b>Macro</b>"]
            SEC_R["<b>SEC</b>"]
            STATS["<b>Statistics</b>"]
            STRAT["<b>Strategy</b>"]
            QUANT["<b>Quant</b>"]
        end
    end

    subgraph MiddleOffice["Middle Office"]
        subgraph RiskMgmt["Risk Management"]
            RISK["<b>Risk Manager</b><br/>VETO Authority"]
            PORT["<b>Portfolio Manager</b>"]
        end
        subgraph IntelDiv["Intelligence Division"]
            ICHIEF["<b>Intel Chief</b>"]
            NEWS["<b>News</b>"]
            GEO["<b>Geopolitical</b>"]
            SOCIAL["<b>Social</b>"]
            CONG["<b>Congress</b>"]
        end
    end

    subgraph BackOffice["Back Office"]
        subgraph OpsDiv["Operations"]
            CODE_R["<b>Code Review</b>"]
            DESIGN_R["<b>Design Review</b>"]
            SEC_REV["<b>Security Review</b>"]
            TOK["<b>Token Optimizer</b>"]
            DEVOPS["<b>DevOps</b>"]
        end
    end

    subgraph ExternalAPIs["External Data Sources"]
        YF["yfinance"]
        FRED["FRED API"]
        EDGAR["SEC EDGAR"]
        GDELT_API["GDELT"]
        REDDIT["Reddit/PRAW"]
        POLY["Polymarket"]
        CONG_API["Congress API"]
    end

    subgraph Outputs["Output Channels"]
        HTML["HTML Reports<br/>GitHub Pages"]
        TG["Telegram Bot"]
        JSON_OUT["JSON State Files"]
    end

    USER --> CIO
    USER --> COO
    CIO --> TradingDesk
    CIO --> ResearchDiv
    CIO --> RiskMgmt
    CIO --> IntelDiv
    COO --> OpsDiv

    TradingDesk --> ExternalAPIs
    ResearchDiv --> ExternalAPIs
    IntelDiv --> ExternalAPIs

    CIO --> Outputs
    RiskMgmt -.->|VETO| CIO

    classDef user fill:#4a1a4a,color:#fff,stroke:#e056fd,stroke-width:3px
    classDef exec fill:#1a1a2e,color:#fff,stroke:#e94560,stroke-width:2px
    classDef front fill:#0e2a4a,color:#fff,stroke:#4ecdc4,stroke-width:2px
    classDef middle fill:#4a0e0e,color:#fff,stroke:#ff6b6b,stroke-width:2px
    classDef back fill:#2a2a2a,color:#fff,stroke:#95a5a6,stroke-width:2px
    classDef external fill:#1a3a1a,color:#fff,stroke:#2ecc71,stroke-width:2px
    classDef output fill:#2a1a0e,color:#fff,stroke:#f39c12,stroke-width:2px

    class USER user
    class CIO,COO exec
    class DDM,MKT,SWS,MACRO,SEC_R,STATS,STRAT,QUANT front
    class RISK,PORT,ICHIEF,NEWS,GEO,SOCIAL,CONG middle
    class CODE_R,DESIGN_R,SEC_REV,TOK,DEVOPS back
    class YF,FRED,EDGAR,GDELT_API,REDDIT,POLY,CONG_API external
    class HTML,TG,JSON_OUT output
```

---

## 2. Logical Architecture

The five logical processing layers that data passes through, from raw ingestion to actionable output.

```mermaid
graph LR
    subgraph L1["Layer 1: Ingestion"]
        direction TB
        I1["yfinance<br/>Prices & VIX"]
        I2["FRED API<br/>CPI, GDP, Rates"]
        I3["SEC EDGAR<br/>Filings & 13F"]
        I4["GDELT<br/>Geopolitical Events"]
        I5["Reddit/PRAW<br/>Social Sentiment"]
        I6["Polymarket<br/>Prediction Markets"]
        I7["Congress API<br/>Stock Trades"]
        I8["RSS Feeds<br/>Financial News"]
    end

    subgraph L2["Layer 2: Processing"]
        direction TB
        P1["Drawdown Calculator"]
        P2["Macro Indicator Parser"]
        P3["Filing Analyzer"]
        P4["Event Classifier"]
        P5["Sentiment Analyzer"]
        P6["Market Categorizer"]
        P7["Member Rater"]
        P8["Article Categorizer"]
    end

    subgraph L3["Layer 3: Analysis"]
        direction TB
        A1["Signal State Machine<br/>WATCH to TARGET"]
        A2["14-Factor Confidence<br/>Scoring Engine"]
        A3["Regime Detection<br/>BULL / BEAR / RANGE"]
        A4["Strategy Backtesting<br/>& Forecasting"]
        A5["Factor Weight<br/>Learning"]
    end

    subgraph L4["Layer 4: Decision"]
        direction TB
        D1["Risk Veto Check<br/>5 rejection criteria"]
        D2["Position Sizing<br/>Fixed-Fraction & Kelly"]
        D3["CIO Synthesis<br/>Unified Report"]
    end

    subgraph L5["Layer 5: Output"]
        direction TB
        O1["HTML Dashboard<br/>8-page report"]
        O2["Telegram Alerts<br/>Real-time notifications"]
        O3["JSON Persistence<br/>State & history"]
        O4["GitHub Pages<br/>Public dashboard"]
    end

    L1 --> L2 --> L3 --> L4 --> L5

    classDef ingest fill:#0e3a2a,color:#fff,stroke:#2ecc71,stroke-width:2px
    classDef process fill:#0e2a4a,color:#fff,stroke:#4ecdc4,stroke-width:2px
    classDef analyze fill:#2a1a0e,color:#fff,stroke:#f39c12,stroke-width:2px
    classDef decide fill:#4a0e0e,color:#fff,stroke:#ff6b6b,stroke-width:2px
    classDef output fill:#1a1a2e,color:#fff,stroke:#e94560,stroke-width:2px

    class I1,I2,I3,I4,I5,I6,I7,I8 ingest
    class P1,P2,P3,P4,P5,P6,P7,P8 process
    class A1,A2,A3,A4,A5 analyze
    class D1,D2,D3 decide
    class O1,O2,O3,O4 output
```

---

## 3. Physical Architecture

The physical runtime environment showing where components execute and where data resides.

```mermaid
graph TB
    subgraph Host["Windows 11 Pro (Local Machine)"]
        subgraph Runtime["Python Runtime"]
            UV["<b>uv</b><br/>Package Manager<br/><i>C:\\Users\\.local\\bin\\uv.exe</i>"]
            PY["<b>Python 3.12</b><br/>Virtual Environment<br/><i>.venv/</i>"]
            APP["<b>Application</b><br/><i>src/app/</i><br/>21 modules"]
        end

        subgraph Scheduler["Windows Task Scheduler"]
            PRE["<b>FinAgents_PreMarket</b><br/>7:00 AM ET weekdays"]
            POST["<b>FinAgents_PostMarket</b><br/>4:30 PM ET weekdays"]
        end

        subgraph FileSystem["Local File System"]
            SRC["<b>src/app/</b><br/>Source code<br/>21 modules"]
            DATA["<b>data/</b><br/>Runtime state<br/><i>gitignored</i>"]
            DOCS["<b>docs/</b><br/>HTML reports<br/>& architecture"]
            AGENTS["<b>.claude/agents/</b><br/>23 agent definitions"]
            SKILLS["<b>.claude/skills/</b><br/>17 skill definitions"]
            LOGS["<b>data/logs/</b><br/>Scheduler logs<br/><i>gitignored</i>"]
        end

        subgraph DataFiles["data/ Contents"]
            SIG["signals.json"]
            PORTF["portfolio.json"]
            HIST["portfolio_history.json"]
            STRAT_D["strategy_*.json"]
            OUT["outcomes.json"]
            SCHED["scheduler_status.json"]
            AGILE_D["agile/*.json"]
            FINOPS_D["finops/*.json"]
            DEVOPS_D["devops/*.json"]
        end

        CLAUDE["<b>Claude CLI</b><br/>Agent Runtime"]
    end

    subgraph GitHub["GitHub (Remote)"]
        REPO["<b>bikoman57/claude</b><br/>Source Repository"]
        PAGES["<b>GitHub Pages</b><br/>bikoman57.github.io/claude<br/>HTML Reports"]
    end

    subgraph ExternalServices["External Services"]
        TG_SVC["<b>Telegram</b><br/>Bot API"]
        YF_SVC["<b>Yahoo Finance</b><br/>Market Data"]
        FRED_SVC["<b>FRED</b><br/>Economic Data"]
        EDGAR_SVC["<b>SEC EDGAR</b><br/>Filings"]
        GDELT_SVC["<b>GDELT</b><br/>Events"]
    end

    UV --> PY --> APP
    Scheduler --> Runtime
    APP --> DataFiles
    APP --> DOCS
    CLAUDE --> AGENTS
    CLAUDE --> SKILLS
    DOCS -->|git push| PAGES
    SRC -->|git push| REPO
    APP --> ExternalServices
    APP --> TG_SVC

    classDef host fill:#1a1a2e,color:#fff,stroke:#e94560,stroke-width:2px
    classDef runtime fill:#0e2a4a,color:#fff,stroke:#4ecdc4,stroke-width:2px
    classDef storage fill:#2a1a0e,color:#fff,stroke:#f39c12,stroke-width:2px
    classDef remote fill:#0e3a2a,color:#fff,stroke:#2ecc71,stroke-width:2px
    classDef external fill:#4a0e0e,color:#fff,stroke:#ff6b6b,stroke-width:2px

    class UV,PY,APP,CLAUDE runtime
    class SRC,DATA,DOCS,AGENTS,SKILLS,LOGS,SIG,PORTF,HIST,STRAT_D,OUT,SCHED,AGILE_D,FINOPS_D,DEVOPS_D storage
    class REPO,PAGES remote
    class TG_SVC,YF_SVC,FRED_SVC,EDGAR_SVC,GDELT_SVC external
    class PRE,POST host
```

---

## 4. Infrastructure / Cloud Architecture

Local infrastructure and all external service dependencies with authentication methods.

```mermaid
graph TB
    subgraph Local["Local Infrastructure (Windows 11)"]
        direction TB
        MACHINE["<b>Developer Machine</b><br/>Windows 11 Pro"]
        TASK_SCHED["<b>Task Scheduler</b><br/>Pre/Post Market Jobs"]
        PYTHON_ENV["<b>Python 3.12 + uv</b><br/>Virtual Environment"]
        CLAUDE_RT["<b>Claude CLI</b><br/>AI Agent Runtime"]
        FILE_STORE["<b>Local JSON Store</b><br/>data/*.json"]
    end

    subgraph GitHubCloud["GitHub Cloud"]
        GH_REPO["<b>Source Repository</b><br/>bikoman57/claude"]
        GH_PAGES["<b>GitHub Pages</b><br/>Static HTML Reports"]
        GH_ACTIONS["<b>CI (future)</b><br/>Linting & Tests"]
    end

    subgraph MarketData["Market Data APIs"]
        YF_API["<b>Yahoo Finance</b><br/><i>No auth required</i><br/>Prices, VIX, Earnings"]
        FRED_API["<b>FRED API</b><br/><i>API Key: FRED_API_KEY</i><br/>CPI, GDP, Rates, Unemployment"]
    end

    subgraph GovData["Government Data APIs"]
        SEC_API["<b>SEC EDGAR</b><br/><i>Email: SEC_EDGAR_EMAIL</i><br/>10-K, 10-Q, 8-K, 13F"]
        CONG_APIG["<b>Congress API</b><br/><i>No auth required</i><br/>STOCK Act Disclosures"]
    end

    subgraph IntelData["Intelligence Data APIs"]
        GDELT_APIG["<b>GDELT</b><br/><i>No auth required</i><br/>Geopolitical Events"]
        REDDIT_API["<b>Reddit / PRAW</b><br/><i>OAuth2: CLIENT_ID/SECRET</i><br/>Social Sentiment"]
        POLY_API["<b>Polymarket</b><br/><i>No auth required</i><br/>Prediction Markets"]
        RSS["<b>RSS Feeds</b><br/><i>No auth required</i><br/>Financial News"]
    end

    subgraph Messaging["Messaging"]
        TG_API["<b>Telegram Bot API</b><br/><i>Bot Token + Chat ID</i><br/>Notifications & Commands"]
    end

    subgraph AI["AI Infrastructure"]
        ANTHROPIC["<b>Anthropic API</b><br/><i>API Key via Claude CLI</i><br/>opus / sonnet / haiku"]
    end

    Local -->|git push| GitHubCloud
    Local -->|HTTP/REST| MarketData
    Local -->|HTTP/REST| GovData
    Local -->|HTTP/REST| IntelData
    Local -->|HTTP/REST| Messaging
    CLAUDE_RT -->|API calls| AI

    classDef local fill:#1a1a2e,color:#fff,stroke:#e94560,stroke-width:2px
    classDef github fill:#0e3a2a,color:#fff,stroke:#2ecc71,stroke-width:2px
    classDef market fill:#0e2a4a,color:#fff,stroke:#4ecdc4,stroke-width:2px
    classDef gov fill:#2a1a0e,color:#fff,stroke:#f39c12,stroke-width:2px
    classDef intel fill:#3a1a3a,color:#fff,stroke:#e056fd,stroke-width:2px
    classDef msg fill:#4a0e0e,color:#fff,stroke:#ff6b6b,stroke-width:2px
    classDef ai fill:#4a4a0e,color:#fff,stroke:#f1c40f,stroke-width:2px

    class MACHINE,TASK_SCHED,PYTHON_ENV,CLAUDE_RT,FILE_STORE local
    class GH_REPO,GH_PAGES,GH_ACTIONS github
    class YF_API,FRED_API market
    class SEC_API,CONG_APIG gov
    class GDELT_APIG,REDDIT_API,POLY_API,RSS intel
    class TG_API msg
    class ANTHROPIC ai
```

---

## 5. Deployment Architecture

How the system is deployed, scheduled, and delivers outputs to end users.

```mermaid
graph LR
    subgraph Trigger["Trigger"]
        TS["<b>Windows Task Scheduler</b>"]
        MANUAL["<b>Manual CLI</b><br/>uv run python -m app..."]
        TG_CMD["<b>Telegram Command</b><br/>/report, /scan, /analyze"]
    end

    subgraph PreMarket["Pre-Market Run (7:00 AM ET)"]
        direction TB
        PM1["Standup Ceremony"]
        PM2["25-Module Data Pipeline"]
        PM3["HTML Report Generation"]
        PM4["Claude CIO Analysis"]
        PM5["Telegram Delivery"]
        PM6["Token & Health Tracking"]
        PM7["Sprint Planning<br/><i>Mondays only</i>"]
        PM1 --> PM2 --> PM3 --> PM4 --> PM5 --> PM6
        PM1 -.-> PM7
    end

    subgraph PostMarket["Post-Market Run (4:30 PM ET)"]
        direction TB
        PO1["25-Module Data Pipeline"]
        PO2["HTML Report Generation"]
        PO3["Claude CIO Analysis"]
        PO4["Telegram Delivery"]
        PO5["Token & Health Tracking"]
        PO6["Postmortem Detection"]
        PO7["Sprint Retrospective<br/><i>Fridays only</i>"]
        PO1 --> PO2 --> PO3 --> PO4 --> PO5 --> PO6
        PO6 -.-> PO7
    end

    subgraph Publish["Publishing"]
        GIT["<b>git push</b><br/>docs/reports/"]
        GHPAGES["<b>GitHub Pages</b><br/>Public Dashboard"]
    end

    subgraph Notify["Notifications"]
        TG_OUT["<b>Telegram Bot</b><br/>Daily Report Summary"]
    end

    TS -->|Weekday AM| PreMarket
    TS -->|Weekday PM| PostMarket
    MANUAL --> PreMarket
    MANUAL --> PostMarket
    TG_CMD -->|listener.py| PreMarket

    PreMarket --> Publish
    PostMarket --> Publish
    Publish --> GHPAGES
    PreMarket --> Notify
    PostMarket --> Notify

    classDef trigger fill:#4a1a4a,color:#fff,stroke:#e056fd,stroke-width:2px
    classDef pre fill:#0e2a4a,color:#fff,stroke:#4ecdc4,stroke-width:2px
    classDef post fill:#2a1a0e,color:#fff,stroke:#f39c12,stroke-width:2px
    classDef publish fill:#0e3a2a,color:#fff,stroke:#2ecc71,stroke-width:2px
    classDef notify fill:#4a0e0e,color:#fff,stroke:#ff6b6b,stroke-width:2px

    class TS,MANUAL,TG_CMD trigger
    class PM1,PM2,PM3,PM4,PM5,PM6,PM7 pre
    class PO1,PO2,PO3,PO4,PO5,PO6,PO7 post
    class GIT,GHPAGES publish
    class TG_OUT notify
```

---

## 6. Application Architecture

Application entry points, orchestration modes, and how the scheduler drives module execution.

```mermaid
graph TB
    subgraph EntryPoints["Entry Points"]
        CLI["<b>CLI Commands</b><br/>uv run python -m app.MODULE CMD"]
        SCHED_EP["<b>Scheduler</b><br/>app.scheduler pre-market<br/>app.scheduler post-market"]
        TG_LISTEN["<b>Telegram Listener</b><br/>app.telegram listen"]
        AGENT_EP["<b>Claude Agent</b><br/>.claude/agents/*.md"]
    end

    subgraph Orchestration["Orchestration Modes"]
        SOLO["<b>Solo Mode</b><br/>CIO runs 25 CLIs<br/>sequentially<br/><i>Default</i>"]
        TEAM["<b>Team Mode</b><br/>CIO spawns 13<br/>parallel teammates<br/><i>Experimental</i>"]
    end

    subgraph SchedulerPipeline["Scheduler Pipeline (25 Modules)"]
        direction TB
        S_ETF["ETF: scan, active"]
        S_MACRO["Macro: dashboard, yields,<br/>rates, calendar"]
        S_SEC["SEC: recent, institutional"]
        S_INTEL["Intel: geopolitical, social,<br/>news, congress, polymarket"]
        S_STATS["Stats: dashboard"]
        S_STRAT["Strategy: proposals, backtest,<br/>forecast, verify"]
        S_RESEARCH["Research: summary"]
        S_RISK["Risk: dashboard"]
        S_PORT["Portfolio: dashboard, snapshot"]
        S_QUANT["Quant: summary"]
        S_HIST["History: weights, summary"]

        S_ETF --> S_MACRO --> S_SEC --> S_INTEL
        S_INTEL --> S_STATS --> S_STRAT --> S_RESEARCH
        S_RESEARCH --> S_RISK --> S_PORT --> S_QUANT --> S_HIST
    end

    subgraph ReportGen["Report Generation"]
        TEXT_RPT["<b>Text Report</b><br/>scheduler/report.py"]
        HTML_RPT["<b>HTML Dashboard</b><br/>scheduler/html_report.py<br/>8 pages"]
        PUBLISH["<b>Publisher</b><br/>scheduler/publisher.py<br/>git push to docs/"]
    end

    subgraph Delivery["Delivery"]
        GH_PG["GitHub Pages"]
        TG_BOT["Telegram Bot"]
    end

    CLI --> SchedulerPipeline
    SCHED_EP --> SchedulerPipeline
    TG_LISTEN --> CLI
    AGENT_EP --> Orchestration
    SOLO --> SchedulerPipeline
    TEAM --> SchedulerPipeline
    SchedulerPipeline --> ReportGen
    TEXT_RPT --> TG_BOT
    HTML_RPT --> PUBLISH --> GH_PG

    classDef entry fill:#4a1a4a,color:#fff,stroke:#e056fd,stroke-width:2px
    classDef orch fill:#1a1a2e,color:#fff,stroke:#e94560,stroke-width:2px
    classDef pipeline fill:#0e2a4a,color:#fff,stroke:#4ecdc4,stroke-width:2px
    classDef report fill:#2a1a0e,color:#fff,stroke:#f39c12,stroke-width:2px
    classDef delivery fill:#0e3a2a,color:#fff,stroke:#2ecc71,stroke-width:2px

    class CLI,SCHED_EP,TG_LISTEN,AGENT_EP entry
    class SOLO,TEAM orch
    class S_ETF,S_MACRO,S_SEC,S_INTEL,S_STATS,S_STRAT,S_RESEARCH,S_RISK,S_PORT,S_QUANT,S_HIST pipeline
    class TEXT_RPT,HTML_RPT,PUBLISH report
    class GH_PG,TG_BOT delivery
```
