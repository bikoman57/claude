# Architecture Diagrams

> 20 Mermaid diagrams documenting the Financial Analysis Agents system at every architectural level. All diagrams render natively in VS Code markdown preview and on GitHub.

---

## Quick Navigation

| # | Category | File | Diagrams | Focus |
|---|----------|------|----------|-------|
| 1 | **Core Architecture** | [core-architecture.md](core-architecture.md) | 6 | System overview, logical layers, physical layout, infrastructure, deployment, application |
| 2 | **Data Architecture** | [data-architecture.md](data-architecture.md) | 5 | Data stores, data flow, ETL pipeline, data platform, signal state machine & confidence model |
| 3 | **Software Design** | [software-architecture.md](software-architecture.md) | 5 | Components, agents, CLI API tree, module integration, layered architecture |
| 4 | **Enterprise** | [enterprise-architecture.md](enterprise-architecture.md) | 4 | Enterprise view, business capabilities, solution flow, application landscape |

---

## All 20 Diagrams

### Core Architecture (6)
1. **System Architecture** — High-level overview: Board to outputs through 6 departments
2. **Logical Architecture** — 5 processing layers: Ingestion to Output
3. **Physical Architecture** — Windows 11 host, file system, runtime environment
4. **Infrastructure / Cloud** — Local machine + GitHub + 8 external APIs
5. **Deployment Architecture** — Task Scheduler, pre/post-market runs, publishing pipeline
6. **Application Architecture** — Entry points, orchestration modes, scheduler pipeline

### Data Architecture (5)
7. **Data Architecture** — All JSON data stores with schemas and owning modules
8. **Data Flow Diagram** — 8 sources through classifiers to confidence scoring to outputs
9. **ETL / Pipeline** — 25-module scheduler pipeline: Extract, Transform, Load
10. **Data Platform** — JSON storage layer, learning engine, feedback loop
11. **Information Architecture** — Signal state machine, 14-factor model, risk veto decision tree

### Software Design (5)
12. **Component Architecture** — 21 Python modules with key types and dependencies
13. **Service / Agent Architecture** — 23 agents by model tier, Solo vs Team modes
14. **API Architecture** — CLI command tree for all module entry points
15. **Integration Architecture** — Producers, consumers, orchestrators, cross-cutting concerns
16. **Layered Architecture** — 6 layers: Presentation to External Services

### Enterprise (4)
17. **Enterprise Architecture** — Business, Application, Data, Technology domains
18. **Business Capability Map** — Strategic, Core, and Supporting capabilities
19. **Solution Architecture** — End-to-end: data collection to learning loop
20. **Application Landscape** — 21 modules by Front/Middle/Back office

---

## Related Docs
- [Organizational Chart](../org-chart.md) — Agent roster, team report flow, naming conventions
