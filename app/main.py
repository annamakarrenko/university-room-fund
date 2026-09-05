from fastapi import FastAPI

app = FastAPI(
    title="University Room Fund",
    description="API для учета аудиторного фонда университета",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "university-room-fund",
    }