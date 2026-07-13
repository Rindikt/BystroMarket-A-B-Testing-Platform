from fastapi import FastAPI
from routers import router

app = FastAPI()
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "analytics_api"}

app.include_router(router)