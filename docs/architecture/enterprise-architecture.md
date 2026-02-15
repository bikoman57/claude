# Enterprise & Business Architecture Diagrams

---

## 1. Enterprise Architecture (Zachman-Inspired)

Full enterprise view across four architectural domains: Business, Application, Data, and Technology.

```mermaid
graph TB
    subgraph Business["Business Architecture"]
        direction LR
        BS["<b>Strategy</b><br/>Leveraged ETF<br/>mean-reversion<br/>swing trading"]
        BP["<b>Process</b><br/>Monitor drawdowns<br/>Score confidence<br/>Check risk → Enter<br/>Track P&L → Exit"]
        BO["<b>Organization</b><br/>Board → Executive<br/>→ Front Office<br/>→ Middle Office<br/>→ Back Office"]
        BM["<b>Metrics</b><br/>Win rate, Sharpe<br/>Factor weights<br/>Token ROI"]
    end

    subgraph Application["Application Architecture"]
        direction LR
        AT["<b>Trading Apps</b><br/>etf, risk, portfolio<br/>strategy, quant"]
        AI_APP["<b>Intelligence Apps</b><br/>news, geopolitical<br/>social, congress<br/>polymarket"]
        AM["<b>Market Data Apps</b><br/>macro, sec<br/>statistics"]
        AP["<b>Platform Apps</b><br/>scheduler, telegram<br/>agile, finops, devops"]
    end

    subgraph Data["Data Architecture"]
        direction LR
        DL["<b>Live State</b><br/>signals.json<br/>portfolio.json"]
        DH["<b>Historical</b><br/>outcomes.json<br/>portfolio_history.json<br/>strategy_*.json"]
        DW["<b>Learned Weights</b><br/>history/weights.json<br/>Factor predictive power"]
        DO["<b>Operational</b><br/>agile/, finops/<br/>devops/, postmortems/"]
    end

    subgraph Technology["Technology Architecture"]
        direction LR
        TW["<b>Runtime</b><br/>Windows 11<br/>Python 3.12<br/>uv package mgr"]
        TC["<b>AI Engine</b><br/>Claude CLI<br/>opus/sonnet/haiku<br/>23 agents"]
        TE["<b>External</b><br/>8 data APIs<br/>Telegram Bot API<br/>GitHub Pages"]
        TI["<b>Infrastructure</b><br/>Task Scheduler<br/>Local JSON store<br/>Git version control"]
    end

    Business --> Application --> Data --> Technology

    classDef biz fill:#4a1a4a,color:#fff,stroke:#e056fd,stroke-width:2px
    classDef app fill:#0e2a4a,color:#fff,stroke:#4ecdc4,stroke-width:2px
    classDef data fill:#2a1a0e,color:#fff,stroke:#f39c12,stroke-width:2px
    classDef tech fill:#0e3a2a,color:#fff,stroke:#2ecc71,stroke-width:2px

    class BS,BP,BO,BM biz
    class AT,AI_APP,AM,AP app
    class DL,DH,DW,DO data
    class TW,TC,TE,TI tech
```

---

## 2. Business Capability Map

What the business can do — organized by strategic, core, and supporting capabilities.

```mermaid
graph TB
    subgraph Strategic["Strategic Capabilities"]
        direction LR
        SC1["<b>Market Intelligence</b><br/>Multi-source sentiment<br/>Geopolitical monitoring<br/>Congressional trading<br/>Prediction markets"]
        SC2["<b>Quantitative Research</b><br/>Regime detection<br/>Factor analysis<br/>Strategy backtesting<br/>Recovery statistics"]
        SC3["<b>AI Orchestration</b><br/>23-agent system<br/>CIO synthesis<br/>Solo & team modes<br/>Cross-domain reasoning"]
    end

    subgraph Core["Core Capabilities"]
        direction LR
        CC1["<b>Signal Generation</b><br/>Drawdown monitoring<br/>State machine lifecycle<br/>8 leveraged ETFs<br/>Alert thresholds"]
        CC2["<b>Confidence Scoring</b><br/>14-factor model<br/>Learned factor weights<br/>HIGH/MEDIUM/LOW<br/>Contrarian logic"]
        CC3["<b>Risk Management</b><br/>5-criterion veto gate<br/>Exposure calculation<br/>Position limits<br/>Sector concentration"]
        CC4["<b>Portfolio Management</b><br/>Position tracking<br/>Kelly & fixed-fraction sizing<br/>P&L monitoring<br/>Daily snapshots"]
    end

    subgraph Supporting["Supporting Capabilities"]
        direction LR
        SP1["<b>Reporting</b><br/>8-page HTML dashboard<br/>Telegram notifications<br/>GitHub Pages publishing"]
        SP2["<b>Operations</b><br/>Code/security review<br/>Token cost tracking<br/>Pipeline health<br/>DevOps monitoring"]
        SP3["<b>Agile Management</b><br/>Sprint planning<br/>Daily standups<br/>Retrospectives<br/>OKR tracking"]
        SP4["<b>Learning System</b><br/>Trade outcome recording<br/>Factor weight computation<br/>Postmortem analysis<br/>Strategy improvement"]
    end

    Strategic --> Core --> Supporting

    classDef strategic fill:#4a1a4a,color:#fff,stroke:#e056fd,stroke-width:2px
    classDef core fill:#4a0e0e,color:#fff,stroke:#ff6b6b,stroke-width:2px
    classDef support fill:#0e2a4a,color:#fff,stroke:#4ecdc4,stroke-width:2px

    class SC1,SC2,SC3 strategic
    class CC1,CC2,CC3,CC4 core
    class SP1,SP2,SP3,SP4 support
```

---

## 3. Solution Architecture

End-to-end solution flow: from raw market data to actionable trading decisions and continuous learning.

```mermaid
graph LR
    subgraph Phase1["Phase 1: Data Collection"]
        D1["Price Data<br/><i>yfinance</i>"]
        D2["Macro Data<br/><i>FRED API</i>"]
        D3["Regulatory<br/><i>SEC EDGAR</i>"]
        D4["Intelligence<br/><i>GDELT, Reddit<br/>News, Congress<br/>Polymarket</i>"]
    end

    subgraph Phase2["Phase 2: Signal Detection"]
        S1["Calculate<br/>drawdown<br/>from ATH"]
        S2["State machine<br/>WATCH → ALERT<br/>→ SIGNAL"]
        S3["Identify<br/>ETF candidates<br/>above threshold"]
    end

    subgraph Phase3["Phase 3: Confidence Scoring"]
        C1["Evaluate<br/>14 factors"]
        C2["Apply learned<br/>factor weights"]
        C3["Score:<br/>HIGH / MED / LOW"]
    end

    subgraph Phase4["Phase 4: Risk Gate"]
        R1["Check 5<br/>veto criteria"]
        R2{"Pass?"}
        R3["Calculate<br/>position size"]
        R4["VETO<br/>Entry blocked"]
    end

    subgraph Phase5["Phase 5: Execution"]
        E1["Entry<br/>recommendation<br/>with price levels"]
        E2["Active position<br/>monitoring"]
        E3["Exit at<br/>profit target<br/>10%"]
    end

    subgraph Phase6["Phase 6: Learning"]
        L1["Record<br/>trade outcome"]
        L2["Update<br/>factor weights"]
        L3["Run<br/>postmortem"]
        L4["Improve<br/>thresholds"]
    end

    Phase1 --> Phase2 --> Phase3 --> Phase4
    R2 -->|Yes| R3 --> Phase5
    R2 -->|No| R4
    Phase5 --> Phase6
    Phase6 -->|feedback| Phase3

    classDef collect fill:#0e3a2a,color:#fff,stroke:#2ecc71,stroke-width:2px
    classDef detect fill:#0e2a4a,color:#fff,stroke:#4ecdc4,stroke-width:2px
    classDef score fill:#2a1a0e,color:#fff,stroke:#f39c12,stroke-width:2px
    classDef risk fill:#4a0e0e,color:#fff,stroke:#ff6b6b,stroke-width:2px
    classDef exec fill:#4a1a4a,color:#fff,stroke:#e056fd,stroke-width:2px
    classDef learn fill:#1a1a2e,color:#fff,stroke:#e94560,stroke-width:2px

    class D1,D2,D3,D4 collect
    class S1,S2,S3 detect
    class C1,C2,C3 score
    class R1,R2,R3,R4 risk
    class E1,E2,E3 exec
    class L1,L2,L3,L4 learn
```

---

## 4. Application Landscape

All 21 modules positioned by business domain (front/middle/back office) with key interactions.

```mermaid
graph TB
    subgraph FrontOffice["Front Office — Revenue Generation"]
        subgraph SignalGen["Signal Generation"]
            ETF_APP["<b>etf</b><br/>Drawdown + signals<br/>+ confidence scoring"]
        end
        subgraph Trading_APP["Trading Analysis"]
            STRAT_APP["<b>strategy</b><br/>Backtesting<br/>Proposals & forecasts"]
            QUANT_APP["<b>quant</b><br/>Regime detection<br/>Recovery stats"]
        end
        subgraph MarketData_APP["Market Data"]
            MACRO_APP["<b>macro</b><br/>VIX, CPI, GDP<br/>Fed, yields"]
            SEC_APP["<b>sec</b><br/>Filings, 13F<br/>Earnings, fundamentals"]
            STATS_APP["<b>statistics</b><br/>Breadth, rotation<br/>Correlations"]
        end
    end

    subgraph MiddleOffice["Middle Office — Risk & Intelligence"]
        subgraph RiskApps["Risk"]
            RISK_APP["<b>risk</b><br/>Limits, exposure<br/>VETO authority"]
            PORT_APP["<b>portfolio</b><br/>Positions, sizing<br/>P&L tracking"]
        end
        subgraph IntelApps["Intelligence"]
            NEWS_APP["<b>news</b><br/>Financial RSS<br/>Sentiment"]
            GEO_APP["<b>geopolitical</b><br/>GDELT events<br/>Sector impact"]
            SOC_APP["<b>social</b><br/>Reddit, officials<br/>Fed tone"]
            CONG_APP["<b>congress</b><br/>STOCK Act<br/>Member ratings"]
            POLY_APP["<b>polymarket</b><br/>Prediction markets<br/>Probability signals"]
        end
    end

    subgraph BackOffice["Back Office — Operations & Support"]
        subgraph Platform_APP["Platform"]
            SCHED_APP["<b>scheduler</b><br/>Pipeline runner<br/>Report generation"]
            TG_APP["<b>telegram</b><br/>Notifications<br/>Remote commands"]
            RESEARCH_APP["<b>research</b><br/>Findings storage"]
        end
        subgraph LearnApps["Learning"]
            HIST_APP["<b>history</b><br/>Outcomes, weights<br/>Factor learning"]
        end
        subgraph OpsApps["Operations"]
            AGILE_APP["<b>agile</b><br/>Sprints, ceremonies<br/>Roadmap & OKRs"]
            FINOPS_APP["<b>finops</b><br/>Token costs<br/>Department budgets"]
            DEVOPS_APP["<b>devops</b><br/>Pipeline health<br/>Module grades"]
        end
    end

    %% Key integration arrows
    MACRO_APP -->|VIX, Fed, yields| ETF_APP
    SEC_APP -->|filings, earnings| ETF_APP
    NEWS_APP -->|sentiment| ETF_APP
    GEO_APP -->|geopolitical risk| ETF_APP
    SOC_APP -->|social sentiment| ETF_APP
    CONG_APP -->|congress sentiment| ETF_APP
    POLY_APP -->|prediction signals| ETF_APP
    STATS_APP -->|market breadth| ETF_APP

    ETF_APP -->|signals| RISK_APP
    RISK_APP -->|veto/approve| PORT_APP
    PORT_APP -->|sizing| ETF_APP

    STRAT_APP -->|thresholds| ETF_APP
    QUANT_APP -->|regime| ETF_APP
    HIST_APP -->|weights| ETF_APP

    ETF_APP -->|outcomes| HIST_APP
    SCHED_APP -->|runs all| FrontOffice
    SCHED_APP -->|runs all| MiddleOffice
    SCHED_APP -->|report| TG_APP

    classDef front fill:#0e2a4a,color:#fff,stroke:#4ecdc4,stroke-width:2px
    classDef middle fill:#4a0e0e,color:#fff,stroke:#ff6b6b,stroke-width:2px
    classDef back fill:#2a2a2a,color:#fff,stroke:#95a5a6,stroke-width:2px

    class ETF_APP,STRAT_APP,QUANT_APP,MACRO_APP,SEC_APP,STATS_APP front
    class RISK_APP,PORT_APP,NEWS_APP,GEO_APP,SOC_APP,CONG_APP,POLY_APP middle
    class SCHED_APP,TG_APP,RESEARCH_APP,HIST_APP,AGILE_APP,FINOPS_APP,DEVOPS_APP back
```
