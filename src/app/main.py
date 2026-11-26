
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from scorm_service.api_attempts import router as attempts_router
from scorm_service.api_auth import router as auth_router
from scorm_service.api_content import router as content_router
from scorm_service.api_packages import router as packages_router
from scorm_service.api_runtime_session import router as runtime_router
from scorm_service.demo_page import router as demo_router

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ["SESSION_SECRET"],
    same_site="lax",
    https_only=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true",
)
STATIC_DIR = (
    Path(__file__).resolve().parent.parent
    / "scorm_service"
    / "static"
)

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(packages_router)
app.include_router(demo_router)
app.include_router(attempts_router)
app.include_router(runtime_router)
app.include_router(auth_router)
app.include_router(content_router)
