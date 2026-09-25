from fastapi import FastAPI
from app.config import settings

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok",
            "db_url_masked": settings.database_url.split("@")[-1]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.app_host, port=settings.app_port)
