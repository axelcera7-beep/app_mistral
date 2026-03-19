"""FastAPI application — JobMind (Modular Version)."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import init_db
from app.routers import auth, interview, cover_letter, history, jobs

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Database initialized")
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="JobMind",
    description="Votre assistant IA pour les entretiens, lettres de motivation et recherche d'emploi.",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — permissive for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(interview.router)
app.include_router(cover_letter.router)
app.include_router(history.router)
app.include_router(jobs.router)

# ---------------------------------------------------------------------------
# Serve frontend static files
# ---------------------------------------------------------------------------
_app_dir = Path(__file__).resolve().parent
_candidates = [
    _app_dir.parent / "frontend",              # Docker: /app/frontend
    _app_dir.parent.parent / "frontend",       # Local:  projet-mistral/frontend
]
FRONTEND_DIR = next((p for p in _candidates if p.is_dir()), None)

if FRONTEND_DIR:
    logger.info("Serving frontend from %s", FRONTEND_DIR)

    @app.get("/")
    async def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/interview")
    async def serve_interview():
        return FileResponse(FRONTEND_DIR / "interview.html")

    @app.get("/coverletter")
    async def serve_cover_letter():
        return FileResponse(FRONTEND_DIR / "coverletter.html")

    @app.get("/login")
    async def serve_login():
        return FileResponse(FRONTEND_DIR / "login.html")

    @app.get("/history")
    async def serve_history():
        return FileResponse(FRONTEND_DIR / "history.html")

    @app.get("/jobsearch")
    async def serve_job_search():
        if FRONTEND_DIR:
            return FileResponse(FRONTEND_DIR / "jobsearch.html")
        raise HTTPException(status_code=404, detail="Frontend not found")

    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")