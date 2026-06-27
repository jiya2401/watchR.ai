# 👁️ watchR.ai

> Autonomous Competitive Intelligence Agent for Indian Startups

<p align="center">

![LangGraph](https://img.shields.io/badge/LangGraph-blue)
![Gemini](https://img.shields.io/badge/Gemini-Free-green)
![Playwright](https://img.shields.io/badge/Playwright-orange)
![ChromaDB](https://img.shields.io/badge/ChromaDB-purple) 
</p>


# 🚀 Build Progress

| Phase | Status |
|-------|--------|
| Docker Infrastructure | ✅ |
| Database Layer | ✅ |
| Blog + GitHub Scraper | ✅ |
| RAG Pipeline | ✅ |
| LangGraph Agent | 🚧 |
| React Dashboard | ⏳ |


# Architecture

```text
Blog Scraper ─────┐
                  │
GitHub Scraper ───┤
                  ▼
           Embedding Model
                  ▼
             ChromaDB
                  ▼
            Gemini Flash
                  ▼
          Competitive Report 