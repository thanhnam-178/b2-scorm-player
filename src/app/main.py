from fastapi import FastAPI
from scorm_service.api_packages import router as packages_router
from scorm_service.demo_page import router as demo_router

app = FastAPI()

@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

app.include_router(packages_router)
app.include_router(demo_router)

