# Wayfarer: Personalized Travel Itinerary Planner

An AI-powered full-stack web app that turns a destination, dates, budget and interests into an editable
day-by-day itinerary (attractions, dining, stay and transport), with cost tracking against your budget.

- **Frontend:** React 18 + Vite + React Router (SaaS-style dashboard, trip builder, interactive itinerary)
- **Backend:** FastAPI + Pydantic v2
- **AI:** any OpenAI-compatible LLM endpoint (e.g. Llama-3 on Groq) via prompt engineering, with a built-in
  rule-based planner as an automatic offline fallback
- **Storage:** Supabase (Postgres) when configured, otherwise a local JSON file

## Quick start

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # optional: add keys, see below
uvicorn app.main:app --reload                        # http://127.0.0.1:8000  (docs at /docs)
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                                          # http://localhost:5173
```

The dev server proxies `/api` to the backend, so no CORS configuration is needed.
For production: `npm run build`; the backend automatically serves `frontend/dist` at `/`.

It works with **zero configuration**: with no keys it uses the built-in planner and stores trips in
`backend/data/trips.json`. The sidebar shows which AI and storage mode is active.

## Enabling the AI (Llama-3 or any OpenAI-compatible model)

Set in `backend/.env`:

```
LLM_API_URL=https://api.groq.com/openai/v1/chat/completions
LLM_API_KEY=your_key
LLM_MODEL=llama-3.1-8b-instant
```

Generation sends a structured prompt (destination, dates, group size, budget, pace, stay tier, interests,
notes) and requires strict JSON back. The response is validated; if the call fails, the JSON is malformed,
the day count is wrong or the plan blows the budget by >15%, the app silently falls back to the built-in
planner. Single-day regeneration also accepts an optional instruction (e.g. "more outdoors").

## Enabling Supabase

1. Create a project and run `supabase/schema.sql` in the SQL editor.
2. Set `SUPABASE_URL` and `SUPABASE_KEY` (use the **service role** key; keep it server-side only) in `backend/.env`.
3. Restart the backend; the sidebar will show `Storage: supabase`.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | AI mode and storage backend |
| GET | `/api/trips` | List the caller's trips |
| POST | `/api/trips` | Create a trip and generate its itinerary |
| GET | `/api/trips/{id}` | Fetch one trip |
| PUT | `/api/trips/{id}` | Save edits (title / itinerary); costs are recomputed server-side |
| DELETE | `/api/trips/{id}` | Delete a trip |
| POST | `/api/trips/{id}/regenerate` | Regenerate every day |
| POST | `/api/trips/{id}/days/{day}/regenerate` | Regenerate one day (`{"instruction": "..."}` optional) |

Interactive docs: `http://127.0.0.1:8000/docs`.

## Features mapped to the scenarios

- **Solo weekend:** enter destination, budget, dates and interests; get a balanced plan in seconds.
- **Couple:** choose pace and stay tier, edit any activity, regenerate a single day, watch the cost bar.
- **Group:** set group size and a combined budget; the plan allocates stay, transport and activities
  within it and keeps a 10% contingency buffer.

## Project structure

```
backend/
  app/
    main.py              FastAPI app, CORS, static hosting of the built frontend
    config.py            environment configuration
    schemas.py           Pydantic models (TripRequest, Itinerary, Trip ...)
    deps.py              caller identity (X-User-Id, or Supabase bearer token)
    store.py             LocalStore + SupabaseStore
    routes/trips.py      REST endpoints
    services/
      planner.py         built-in rule-based itinerary engine
      llm.py             prompt engineering + LLM client + validation
      generator.py       LLM-first, built-in fallback
  tests/test_api.py      API tests (pytest)
frontend/src/
  pages/Dashboard.jsx, TripBuilder.jsx, ItineraryView.jsx
  api.js, App.jsx, styles.css
supabase/schema.sql
```

## Tests

```bash
cd backend && pytest -q
```

## Honest notes and limits

- **No transformer models are bundled.** The brief's hardware notes mention local `.keras` Transformer
  models; this project instead calls a hosted LLM through an API (optional) and ships a lightweight
  built-in planner, so it runs on any laptop. Minimum: Python 3.10+, Node 18+, ~1 GB free disk.
- The built-in planner uses curated hints for a few cities (Jaipur, Goa, Paris) and generic templates
  elsewhere. Place names, prices and opening hours are **estimates; verify before booking**. LLM output
  is likewise unverified and may contain errors.
- Identity is an anonymous per-browser id. The backend already accepts Supabase bearer tokens; adding a
  login screen with Supabase Auth is the natural next step.
- Costs are totals for the whole group, not per person.

## Submission links (fill in before review)

- Demo: _add your deployed or recorded demo link here_
- GitHub: _add your repository link here_
