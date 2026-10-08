from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as triage_router

app = FastAPI(
    title="MediFlow API",
    description="API de triaje clínico inteligente con OCI y LLM",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(triage_router)

@app.get("/")
def health_check():
    return {"status": "ok", "app": "MediFlow Backend"}
