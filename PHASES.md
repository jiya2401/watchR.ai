# watchR.ai — Phase by Phase Build Guide
### Start it
```bash
# 1. Edit .env — paste your Gemini API key on line 2
# 2. Run:
docker compose up --build
```

### Demo test — MUST pass before Phase 1
```bash
curl http://localhost:8000/health
# Expected: {"status":"ok","mongo":"ok","redis":"ok","service":"watchr-api"}

curl http://localhost:8000/
# Expected: {"name":"WatchR API","description":"..."}
```

### What to show people at Phase 0
"I have a full production-grade backend running — FastAPI, MongoDB, Redis,
and a Celery worker — all wired together with Docker. This is the same stack
companies like Razorpay use in production."

---

## ◉ PHASE 1 — Scrapers Working
**Time:** 1-2 days  
**What works:** Blog scraper finds and reads engineering blogs.
GitHub scraper fetches repos, commits, languages.
Data saved to MongoDB.

### Test the scrapers directly
```bash
# POST to trigger scrape (uses Celery background task)
curl -X POST "http://localhost:8000/api/analyze/Razorpay"
# Returns: {"job_id":"...","company":"Razorpay","ws_url":"..."}

# Check status
curl "http://localhost:8000/api/analyze/Razorpay/status"
# Watch: step_log fills up as scraper runs
```

### Demo test
```bash
# After 3-5 minutes, check MongoDB has data
# Open: http://localhost:8000/docs
# Try: GET /api/analyze/Razorpay/status
# You should see articles_scraped > 0
```

### What to show people at Phase 1
"The agent autonomously found Razorpay's engineering blog at engineering.razorpay.com,
read 12 articles, and fetched their GitHub — 47 repos, Python/Go/Kotlin as primary
languages, topics: payments, fintech, ml. All without me writing a single URL."

---

## ◉ PHASE 2 — RAG Pipeline Working
**Time:** 1 day  
**What works:** Scraped text is chunked, embedded with Gemini,
and stored in ChromaDB. You can semantically search the collected knowledge.

### Test retrieval
```bash
# After Phase 1 scrape is done, test retrieval via API docs
# Open: http://localhost:8000/docs
# (No direct retrieval endpoint in API — it's internal)
# Instead, check ChromaDB has data by watching logs:
docker compose logs worker | grep "Stored"
# Should show: "Stored 34 chunks for Razorpay [blog]"
```

### What to show people at Phase 2
"Every article is broken into 350-word chunks, embedded with Gemini's
text-embedding-004 model into 768-dimensional vectors, and stored in ChromaDB.
When the agent analyzes tech stack, it semantically searches these vectors —
not keyword search. That's why it can connect 'we use Flink for streaming'
in one article to 'real-time decisioning' in another."

---

## ◉ PHASE 3 — Agent Working (Terminal demo)
**Time:** 2-3 days  
**What works:** Full LangGraph pipeline runs.
6 nodes execute: trigger → await → analyze_tech → analyze_hiring → analyze_product → synthesize.
Report saved to MongoDB.

### Trigger and watch in terminal
```bash
# Terminal 1 — watch worker logs (this is the agent thinking)
docker compose logs -f worker

# Terminal 2 — trigger analysis
curl -X POST "http://localhost:8000/api/analyze/Razorpay"
# Copy the job_id from response

# Terminal 3 — poll status
watch -n 3 'curl -s "http://localhost:8000/api/analyze/Razorpay/status" | python3 -m json.tool'
```

### See the report (JSON)
```bash
curl "http://localhost:8000/api/analyze/Razorpay/report" | python3 -m json.tool
# Should show: tech_signals, hiring_signals, product_signals, executive_summary
```

### What to show people at Phase 3
This is the main demo. Show them the terminal logs. Point to each step:
- "It's triggering the scraper Celery task..."
- "It's polling every 20 seconds until scraping is done..."
- "It's retrieving relevant chunks from ChromaDB and calling Gemini Flash..."
- "Final synthesis uses Gemini Pro — the expensive model — only once..."
"This is a stateful AI agent. Not a chatbot. It makes decisions, uses tools,
waits for async jobs, and writes a report — all autonomously."

---

## ◉ PHASE 4 — Frontend Working (Full demo)
**Time:** 1 day  
**What works:** Complete React UI. Home page, live agent stream, report page.

### Start frontend
```bash
cd frontend
npm install
npm run dev
# Open: http://localhost:5173
```

### Demo flow
1. Open `http://localhost:5173`
2. Type "Zepto" in search box
3. Click Analyze
4. Watch the live agent stream page — terminal logs appear in real time
5. When complete, full intelligence report loads automatically

### What to show people at Phase 4
Switch to the LiveAgent page and let them watch it run.
Point to the pipeline on the left — each step lights up as the agent completes it.
Point to the terminal log on the right — "you're watching the agent think in real time."
When the report loads, walk through all 4 tabs.

---

## ◉ PHASE 5 — Production Ready
**Time:** 1 day  
**What works:** Deployed on Railway (backend) + Vercel (frontend).
Live URL you can share with anyone.

### Deploy backend to Railway
```bash
# 1. railway.app → New Project → Deploy from GitHub
# 2. Add environment variables from .env
# 3. Add Redis and MongoDB plugins
# 4. Set start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Deploy frontend to Vercel
```bash
# 1. vercel.com → New Project → Import GitHub repo
# 2. Set root directory: frontend
# 3. Add env var: VITE_API_URL=https://your-railway-url.railway.app
# 4. Update vite.config.js proxy to point to Railway URL
```

### What to show people at Phase 5
Share the live URL. Let them type any Indian startup.
"This is fully deployed. Anyone can use it. Built entirely on free APIs."

---

## COST TRACKER

| Phase | API calls | Approx cost | 
|-------|-----------|-------------|
| Phase 0 | 0 | ₹0 |
| Phase 1 (per company) | ~30 GitHub API calls | ₹0 |
| Phase 2 (per company) | ~50 embedding calls | ₹0 (free tier) |
| Phase 3 (per company) | ~6 Flash + 1 Pro | ₹0 (free tier) |
| **Total per analysis** | | **₹0** |

Free tier limits: 250 Flash req/day, 50 Pro req/day.
You can run ~8-10 full company analyses per day for free.
