from fastapi import FastAPI

from app.api.datasets import router as datasets_router
from app.api.projects import router as projects_router


app = FastAPI(title="Local Data Science Agent")
app.include_router(projects_router)
app.include_router(datasets_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
