<div align="center">

# 👁️ watchR.ai
### Autonomous Competitive Intelligence Agent for Indian Startups

![LangGraph](https://img.shields.io/badge/LangGraph-blue)
![Gemini](https://img.shields.io/badge/Gemini-Free-green)
![Playwright](https://img.shields.io/badge/Playwright-orange)
![ChromaDB](https://img.shields.io/badge/ChromaDB-purple)

</div>

## What You Get
 
You type a company name. In minutes you get:
 
- **Tech stack signals** — what they're quietly adopting or retiring
- **Hiring pattern analysis** — what product each role signals
- **Product launch predictions** — with confidence scores and timelines
- **AI/ML maturity score** — where they stand vs competitors
- **Executive intelligence brief** — written like a VC research note
**No human input after the company name. The autonomous agent does everything.**
 
 
## Build Progress
 
| Phase | Status |
|-------|--------|
| Docker Infrastructure | ✅ |
| Database Layer | ✅ |
| Blog + GitHub Scraper | ✅ |
| RAG Pipeline | ✅ |
| LangGraph Agent | ✅ |
| React Dashboard | ⏳ |
 
 
## Architecture
 
```mermaid
flowchart TD
    subgraph DataLayer["Data Layer"]
        A1[Blog Scraper<br/>Playwright]
        A2[GitHub Scraper<br/>REST API]
        A3[Gemini Embeddings]
        A4[(ChromaDB)]
        A1 --> A3
        A2 --> A3
        A3 --> A4
    end
 
    subgraph AgentLayer["Agent Layer"]
        B1[LangGraph StateGraph<br/>6 nodes]
        B2[Gemini Flash<br/>× 5 analysis nodes]
        B3[Gemini Pro<br/>× 1 synthesis node]
    end
 
    subgraph StorageAPI["Storage + API"]
        C1[(MongoDB<br/>reports, companies, logs)]
        C2[FastAPI<br/>REST endpoints]
        C3[WebSocket<br/>real-time stream]
    end
 
    subgraph Frontend["React Dashboard"]
        D1[Home<br/>search companies]
        D2[LiveAgent<br/>watch agent think]
        D3[Report<br/>4-tab intelligence report]
    end
 
    DataLayer -->|retrieve| AgentLayer
    AgentLayer --> StorageAPI
    StorageAPI --> Frontend
```
 
 
## Graph Flow
 
```mermaid
flowchart TD
    A[trigger_scrape] --> B[await_scrape]
    B -->|still collecting| B
    B -->|scrape_done = True| C[analyze_tech]
    C --> D[analyze_hiring]
    D --> E[analyze_product]
    E --> F[synthesize]
    F --> G([END])
 
    style G fill:#22c55e,color:#fff
    style A fill:#3b82f6,color:#fff
```
 
## Agent Pipeline — Node by Node
 
| Node | Input | What it does | Output |
|------|-------|-------------|--------|
| `trigger_scrape` | company name | Fires Celery task | task_id |
| `await_scrape` | task_id | Polls until scraping done | blog articles, GitHub data |
| `analyze_tech` | ChromaDB chunks | Finds tech stack signals | TechSignal[] with confidence |
| `analyze_hiring` | ChromaDB chunks | Decodes hiring → initiatives | HiringSignal[] |
| `analyze_product` | ChromaDB chunks | Predicts launches | ProductSignal[] with probability |
| `synthesize` | All signals | Writes executive brief | Executive summary |
 
---
 
<div align="center">
*🚧 Actively developed.*
 
</div>  