import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.admin import setup_admin
from api.routers import auth, crawl_jobs, events, feed, locations, sources, tag_rules

app = FastAPI(title="Momaverse API")

cors_origins = os.environ.get("CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(locations.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(feed.router, prefix="/api/v1")
app.include_router(sources.router, prefix="/api/v1")
app.include_router(crawl_jobs.router, prefix="/api/v1")
app.include_router(tag_rules.router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# SQLAdmin mounted on /admin — must come before the catch-all static mount
setup_admin(app)

# Serve frontend static files — must be last so API routes take priority
# Skipped in Docker where frontend is served from Cloud Storage
_frontend_dir = Path(__file__).resolve().parent.parent.parent / "src"
if _frontend_dir.is_dir():
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
