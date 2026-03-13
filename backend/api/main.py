from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import auth, events, feedback, locations, websites

app = FastAPI(title="Momaverse API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(feedback.router, prefix="/api/v1")
app.include_router(locations.router, prefix="/api/v1")
app.include_router(websites.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
