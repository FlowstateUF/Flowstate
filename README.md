# Flowstate
Flowstate is an AI-assisted educational platform that turns static PDF textbooks into interactive study experiences. Using textbook processing and a RAG pipeline, the platform supports chapter-based pretests, quizzes, summaries, flashcards, and a textbook-aware AI tutor named Flo. Flowstate also includes learning analytics that help users track study activity, performance, and confidence over time.

## Setup
- Make sure all secrets exist in `backend/.env`
- Install Docker Desktop and open it

## Running (from Flowstate root directory)
- `docker compose up` — run in foreground (with logs)
- `docker compose up -d` — run in background (no logs)
- `docker compose up --build` — rebuild images (run this when `requirements.txt` or `package.json` change)
- `Ctrl+C` or `docker compose down` — stop containers

## Redis
- you can go to localhost:8081 to see redis jobs

## Notes
- Code changes (`.py`, `.js`) do not require a rebuild, just start docker like normal
- Dependency changes (e.g. requirments.txt) require running with `--build` (might take longer)
- To free up Docker disk space occasionally: `docker system prune -a`
- If you see "Error pull access denied for..." just ignore it
