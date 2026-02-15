# Software Design & Engineering Diagrams

---

## 1. Component Architecture

All 21 Python modules as components with their key types, responsibilities, and dependencies.

```mermaid
graph TB
    subgraph CoreTrading["Core Trading Components"]
        ETF["<b>etf/</b><br/>SignalState, Signal<br/>ConfidenceScore<br/>DrawdownResult<br/>ETFMapping, Universe"]
        RISK["<b>risk/</b><br/>RiskLimits, VetoResult<br/>ExposureReport<br/>Position"]
        PORT["<b>portfolio/</b><br/>PortfolioConfig<br/>PortfolioPosition<br/>PortfolioSnapshot<br/>PositionSize"]
    end

    subgraph MarketData["Market Data Components"]
        MACRO["<b>macro/</b><br/>MacroIndicators<br/>FedTrajectory<br/>YieldCurveState<br/>EconomicEvent"]
        SEC["<b>sec/</b><br/>SECFiling, Filing13F<br/>EarningsEvent<br/>FundamentalData<br/>IndexHolding"]
        STATS["<b>statistics/</b><br/>BreadthIndicator<br/>SectorRotation<br/>CorrelationMatrix"]
    end

    subgraph Intelligence["Intelligence Components"]
        NEWS["<b>news/</b><br/>NewsArticle<br/>SentimentScore<br/>JournalistProfile"]
        GEO["<b>geopolitical/</b><br/>GDELTEvent<br/>ImpactClassification<br/>EventCategory"]
        SOCIAL["<b>social/</b><br/>RedditPost<br/>FedStatement<br/>SentimentResult"]
        CONG["<b>congress/</b><br/>CongressTrade<br/>MemberProfile<br/>SectorAggregation"]
        POLY["<b>polymarket/</b><br/>PolymarketMarket<br/>MarketCategory<br/>MarketSignal"]
    end

    subgraph StrategyEngine["Strategy Engine"]
        STRAT["<b>strategy/</b><br/>BacktestConfig<br/>BacktestResult<br/>StrategyProposal<br/>PriceTarget"]
        QUANT["<b>quant/</b><br/>MarketRegime<br/>RecoveryStats<br/>SignificanceTest"]
        HIST["<b>history/</b><br/>TradeOutcome<br/>FactorWeight<br/>OutcomeRecorder"]
        RESEARCH["<b>research/</b><br/>ResearchFinding<br/>ResearchStore"]
    end

    subgraph Platform["Platform Components"]
        SCHED["<b>scheduler/</b><br/>SchedulerRun<br/>ModuleResult<br/>HTMLReport<br/>Publisher"]
        TG["<b>telegram/</b><br/>TelegramClient<br/>TelegramConfig<br/>Dispatcher<br/>Listener"]
        AGILE["<b>agile/</b><br/>Sprint, SprintTask<br/>StandupEntry<br/>RetroEntry, OKR"]
        FINOPS["<b>finops/</b><br/>TokenUsageRecord<br/>DepartmentBudget<br/>ROIAnalysis"]
        DEVOPS["<b>devops/</b><br/>ModuleHealth<br/>SystemHealth<br/>PipelineGrade"]
    end

    %% Cross-component dependencies
    ETF -->|drawdowns| RISK
    ETF -->|signals| PORT
    ETF -->|14 factors| MACRO
    ETF -->|14 factors| SEC
    ETF -->|14 factors| NEWS
    ETF -->|14 factors| GEO
    ETF -->|14 factors| SOCIAL
    ETF -->|14 factors| CONG
    ETF -->|14 factors| POLY
    ETF -->|14 factors| STATS
    RISK -->|veto| ETF
    PORT -->|sizing| ETF
    STRAT -->|thresholds| ETF
    QUANT -->|regime| ETF
    HIST -->|weights| ETF
    SCHED -->|runs all| ETF
    SCHED -->|runs all| MACRO
    SCHED -->|runs all| SEC
    SCHED -->|report| TG

    classDef core fill:#4a0e0e,color:#fff,stroke:#ff6b6b,stroke-width:2px
    classDef market fill:#0e2a4a,color:#fff,stroke:#4ecdc4,stroke-width:2px
    classDef intel fill:#0e3a2a,color:#fff,stroke:#2ecc71,stroke-width:2px
    classDef strat fill:#2a1a0e,color:#fff,stroke:#f39c12,stroke-width:2px
    classDef platform fill:#1a1a2e,color:#fff,stroke:#e94560,stroke-width:2px

    class ETF,RISK,PORT core
    class MACRO,SEC,STATS market
    class NEWS,GEO,SOCIAL,CONG,POLY intel
    class STRAT,QUANT,HIST,RESEARCH strat
    class SCHED,TG,AGILE,FINOPS,DEVOPS platform
```

---

## 2. Service / Agent Architecture

23 AI agents organized by model tier and department, with Solo vs Team communication patterns.

```mermaid
graph TB
    subgraph OpusTier["Opus Tier (Complex Reasoning)"]
        CIO["<b>exec-cio</b><br/>Orchestrates all departments<br/>Synthesizes unified report"]
        STRAT_RES["<b>research-strategy-researcher</b><br/>New strategy discovery<br/>Web search + academic research"]
        QUANT_A["<b>research-quant</b><br/>Statistical analysis<br/>Custom Python + regime detection"]
    end

    subgraph SonnetTier["Sonnet Tier (Domain Analysis)"]
        subgraph Trading["Trading (3)"]
            T1["trading-drawdown-monitor"]
            T2["trading-market-analyst"]
            T3["trading-swing-screener"]
        end
        subgraph Research["Research (3)"]
            R1["research-macro"]
            R2["research-sec"]
            R3["research-statistics"]
            R4["research-strategy-analyst"]
        end
        subgraph Intel["Intelligence (5)"]
            IC["intel-chief"]
            I1["intel-news"]
            I2["intel-geopolitical"]
            I3["intel-social"]
            I4["intel-congress"]
        end
        subgraph RiskDept["Risk (2)"]
            RM["risk-manager"]
            RP["risk-portfolio"]
        end
        OD["ops-design-reviewer"]
    end

    subgraph HaikuTier["Haiku Tier (Mechanical Tasks)"]
        COO_A["exec-coo"]
        OC["ops-code-reviewer"]
        OS["ops-security-reviewer"]
        OT["ops-token-optimizer"]
        ODE["ops-devops"]
    end

    subgraph SoloMode["Solo Mode (Sequential)"]
        direction LR
        SM1["CIO runs 25<br/>module CLIs"] --> SM2["Collects all<br/>outputs"] --> SM3["Synthesizes<br/>unified report"]
    end

    subgraph TeamMode["Team Mode (Parallel)"]
        direction LR
        TM1["CIO spawns<br/>13 teammates"] --> TM2["All run in<br/>parallel"] --> TM3["Broadcast findings<br/>[DOMAIN] FORMAT"]
        TM3 --> TM4["CIO waits,<br/>synthesizes"]
    end

    CIO -.->|orchestrates| SoloMode
    CIO -.->|orchestrates| TeamMode

    %% Intel hierarchy
    IC --> I1
    IC --> I2
    IC --> I3
    IC --> I4

    classDef opus fill:#4a1a4a,color:#fff,stroke:#e056fd,stroke-width:3px
    classDef sonnet fill:#0e2a4a,color:#fff,stroke:#4ecdc4,stroke-width:2px
    classDef haiku fill:#2a2a2a,color:#fff,stroke:#95a5a6,stroke-width:2px
    classDef mode fill:#1a1a2e,color:#fff,stroke:#e94560,stroke-width:1px

    class CIO,STRAT_RES,QUANT_A opus
    class T1,T2,T3,R1,R2,R3,R4,IC,I1,I2,I3,I4,RM,RP,OD sonnet
    class COO_A,OC,OS,OT,ODE haiku
    class SM1,SM2,SM3,TM1,TM2,TM3,TM4 mode
```

---

## 3. API Architecture (CLI Command Tree)

All module CLI entry points accessible via `uv run python -m app.MODULE COMMAND`.

```mermaid
graph LR
    ROOT["<b>python -m app</b>"]

    subgraph ETF_CLI["etf"]
        EC1["scan"]
        EC2["active"]
        EC3["universe"]
    end

    subgraph MACRO_CLI["macro"]
        MC1["dashboard"]
        MC2["yields"]
        MC3["rates"]
        MC4["calendar"]
    end

    subgraph SEC_CLI["sec"]
        SC1["recent"]
        SC2["institutional"]
        SC3["earnings"]
        SC4["fundamentals TICKER"]
        SC5["holdings INDEX"]
    end

    subgraph RISK_CLI["risk"]
        RC1["dashboard"]
        RC2["veto TICKER VALUE"]
    end

    subgraph PORT_CLI["portfolio"]
        PC1["dashboard"]
        PC2["snapshot"]
    end

    subgraph STRAT_CLI["strategy"]
        STC1["proposals"]
        STC2["backtest-all"]
        STC3["forecast"]
        STC4["verify"]
    end

    subgraph INTEL_CLI["intelligence"]
        IC1["geopolitical summary"]
        IC2["social summary"]
        IC3["news summary"]
        IC4["congress summary"]
        IC5["polymarket summary"]
    end

    subgraph ANALYSIS_CLI["analysis"]
        AC1["statistics dashboard"]
        AC2["quant summary"]
        AC3["quant regime"]
        AC4["research summary"]
    end

    subgraph HIST_CLI["history"]
        HC1["weights"]
        HC2["summary"]
    end

    subgraph PLATFORM_CLI["platform"]
        PLC1["scheduler pre-market"]
        PLC2["scheduler post-market"]
        PLC3["telegram notify MSG"]
        PLC4["telegram ask MSG"]
        PLC5["telegram listen"]
        PLC6["telegram setup-check"]
        PLC7["agile sprint"]
        PLC8["agile standup"]
        PLC9["devops health"]
    end

    ROOT --> ETF_CLI
    ROOT --> MACRO_CLI
    ROOT --> SEC_CLI
    ROOT --> RISK_CLI
    ROOT --> PORT_CLI
    ROOT --> STRAT_CLI
    ROOT --> INTEL_CLI
    ROOT --> ANALYSIS_CLI
    ROOT --> HIST_CLI
    ROOT --> PLATFORM_CLI

    classDef root fill:#4a1a4a,color:#fff,stroke:#e056fd,stroke-width:3px
    classDef cli fill:#0e2a4a,color:#fff,stroke:#4ecdc4,stroke-width:2px
    classDef cmd fill:#1a1a2e,color:#fff,stroke:#e94560,stroke-width:1px

    class ROOT root
    class ETF_CLI,MACRO_CLI,SEC_CLI,RISK_CLI,PORT_CLI,STRAT_CLI,INTEL_CLI,ANALYSIS_CLI,HIST_CLI,PLATFORM_CLI cli
    class EC1,EC2,EC3,MC1,MC2,MC3,MC4,SC1,SC2,SC3,SC4,SC5,RC1,RC2,PC1,PC2,STC1,STC2,STC3,STC4,IC1,IC2,IC3,IC4,IC5,AC1,AC2,AC3,AC4,HC1,HC2,PLC1,PLC2,PLC3,PLC4,PLC5,PLC6,PLC7,PLC8,PLC9 cmd
```

---

## 4. Integration Architecture

How modules connect to each other: data producers, consumers, and cross-cutting concerns.

```mermaid
graph LR
    subgraph Producers["Data Producers"]
        P_ETF["<b>etf</b><br/>Drawdowns<br/>Signal states"]
        P_MACRO["<b>macro</b><br/>VIX, CPI, GDP<br/>Fed trajectory<br/>Yield curve"]
        P_SEC["<b>sec</b><br/>Filings, 13F<br/>Earnings, Fundamentals"]
        P_INTEL["<b>news + geo +<br/>social + congress +<br/>polymarket</b><br/>Sentiment & events"]
        P_STATS["<b>statistics</b><br/>Breadth, rotation<br/>Correlations"]
    end

    subgraph Core["Core Integrators"]
        CONFIDENCE["<b>etf/confidence.py</b><br/>Consumes ALL producers<br/>Outputs: 14-factor score"]
        VETO_INT["<b>risk/veto.py</b><br/>Consumes: portfolio + signals<br/>Outputs: approve/reject"]
        SIZING["<b>portfolio/sizing.py</b><br/>Consumes: portfolio + risk<br/>Outputs: position size"]
    end

    subgraph Consumers["Data Consumers"]
        C_STRAT["<b>strategy</b><br/>Reads: signals, prices<br/>Writes: backtests, proposals"]
        C_QUANT["<b>quant</b><br/>Reads: prices, signals<br/>Writes: regime, recovery"]
        C_HIST["<b>history</b><br/>Reads: outcomes, factors<br/>Writes: weights"]
    end

    subgraph Orchestrators["Orchestration Layer"]
        SCHEDULER["<b>scheduler</b><br/>Runs all 25 CLIs<br/>Generates reports"]
        AGENTS["<b>Claude Agents</b><br/>CIO synthesizes<br/>across all modules"]
        TELEGRAM["<b>telegram</b><br/>Delivers reports<br/>Receives commands"]
    end

    subgraph CrossCutting["Cross-Cutting Concerns"]
        AGILE_INT["<b>agile</b><br/>Sprint tracking<br/>Ceremonies"]
        FINOPS_INT["<b>finops</b><br/>Token cost tracking"]
        DEVOPS_INT["<b>devops</b><br/>Pipeline health"]
    end

    P_ETF --> CONFIDENCE
    P_MACRO --> CONFIDENCE
    P_SEC --> CONFIDENCE
    P_INTEL --> CONFIDENCE
    P_STATS --> CONFIDENCE

    CONFIDENCE --> VETO_INT
    VETO_INT --> SIZING

    P_ETF --> C_STRAT
    P_ETF --> C_QUANT
    CONFIDENCE --> C_HIST

    SCHEDULER --> Producers
    SCHEDULER --> Core
    SCHEDULER --> Consumers
    AGENTS --> SCHEDULER
    SCHEDULER --> TELEGRAM

    AGILE_INT -.-> SCHEDULER
    FINOPS_INT -.-> AGENTS
    DEVOPS_INT -.-> SCHEDULER

    classDef producer fill:#0e3a2a,color:#fff,stroke:#2ecc71,stroke-width:2px
    classDef core fill:#4a0e0e,color:#fff,stroke:#ff6b6b,stroke-width:3px
    classDef consumer fill:#2a1a0e,color:#fff,stroke:#f39c12,stroke-width:2px
    classDef orch fill:#1a1a2e,color:#fff,stroke:#e94560,stroke-width:2px
    classDef cross fill:#2a2a2a,color:#fff,stroke:#95a5a6,stroke-width:1px

    class P_ETF,P_MACRO,P_SEC,P_INTEL,P_STATS producer
    class CONFIDENCE,VETO_INT,SIZING core
    class C_STRAT,C_QUANT,C_HIST consumer
    class SCHEDULER,AGENTS,TELEGRAM orch
    class AGILE_INT,FINOPS_INT,DEVOPS_INT cross
```

---

## 5. Layered Architecture

Six horizontal layers from presentation down to external services, showing what belongs at each level.

```mermaid
graph TB
    subgraph L1["Presentation Layer"]
        HTML["<b>HTML Dashboard</b><br/>scheduler/html_report.py<br/>8-page dark fintech theme<br/>Chart.js visualizations"]
        TG_UI["<b>Telegram Interface</b><br/>telegram/formatting.py<br/>Markdown messages<br/>Command responses"]
        CLI_UI["<b>CLI Output</b><br/>Each module's __main__.py<br/>Structured text output"]
    end

    subgraph L2["Orchestration Layer"]
        SCHED_L["<b>Scheduler</b><br/>runner.py — 25-module pipeline<br/>scheduled_run.py — pre/post market<br/>publisher.py — git push to Pages"]
        AGENT_L["<b>Agent System</b><br/>23 agents in .claude/agents/<br/>Solo mode vs Team mode<br/>CIO orchestration"]
        TG_L["<b>Telegram Bot</b><br/>listener.py — long-polling<br/>dispatcher.py — command routing<br/>client.py — async HTTP"]
    end

    subgraph L3["Domain Layer"]
        subgraph Trading_L["Trading"]
            ETF_L["etf/signals<br/>etf/drawdown<br/>etf/confidence"]
        end
        subgraph Research_L["Research"]
            STRAT_L["strategy/*<br/>quant/*<br/>research/*"]
        end
        subgraph Intel_L["Intelligence"]
            INTEL_MODS["news/*<br/>geopolitical/*<br/>social/*<br/>congress/*<br/>polymarket/*"]
        end
        subgraph Market_L["Market Data"]
            MKT_MODS["macro/*<br/>sec/*<br/>statistics/*"]
        end
    end

    subgraph L4["Risk & Decision Layer"]
        RISK_L["<b>Risk Management</b><br/>risk/limits.py — RiskLimits<br/>risk/exposure.py — ExposureReport<br/>risk/veto.py — check_veto()"]
        PORT_L["<b>Portfolio Management</b><br/>portfolio/tracker.py — positions<br/>portfolio/sizing.py — Kelly & fixed-fraction"]
    end

    subgraph L5["Data Access Layer"]
        STORES["<b>JSON Stores</b><br/>etf/store.py — signals<br/>history/store.py — outcomes<br/>strategy/store.py — backtests<br/>agile/store.py — sprints<br/>congress/store.py — trades"]
        HISTORY_L["<b>Learning System</b><br/>history/weights.py — factor weights<br/>history/recorder.py — outcome recording"]
    end

    subgraph L6["External Services Layer"]
        EXT["<b>External APIs</b><br/>yfinance — prices, VIX<br/>FRED — macro indicators<br/>SEC EDGAR — filings<br/>GDELT — geopolitical events<br/>Reddit/PRAW — social sentiment<br/>Polymarket — prediction markets<br/>Congress API — STOCK Act<br/>Telegram Bot API — messaging"]
    end

    L1 --> L2 --> L3 --> L4 --> L5 --> L6

    classDef presentation fill:#4a1a4a,color:#fff,stroke:#e056fd,stroke-width:2px
    classDef orchestration fill:#1a1a2e,color:#fff,stroke:#e94560,stroke-width:2px
    classDef domain fill:#0e2a4a,color:#fff,stroke:#4ecdc4,stroke-width:2px
    classDef risk fill:#4a0e0e,color:#fff,stroke:#ff6b6b,stroke-width:2px
    classDef data fill:#2a1a0e,color:#fff,stroke:#f39c12,stroke-width:2px
    classDef external fill:#0e3a2a,color:#fff,stroke:#2ecc71,stroke-width:2px

    class HTML,TG_UI,CLI_UI presentation
    class SCHED_L,AGENT_L,TG_L orchestration
    class ETF_L,STRAT_L,INTEL_MODS,MKT_MODS domain
    class RISK_L,PORT_L risk
    class STORES,HISTORY_L data
    class EXT external
```
