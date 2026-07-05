from fastapi import FastAPI


app = FastAPI(title="Local Data Science Agent")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
