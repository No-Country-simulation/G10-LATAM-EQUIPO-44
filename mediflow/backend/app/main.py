from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.environment import RuntimeSettings, load_environment
from app.core.error_handler import (
    DuplicateReviewError,
    ReviewValidationError,
    ReviewNotFoundError,
    OCITimeoutError,
    OCIPersistenceError,
)

load_environment()
runtime_settings = RuntimeSettings()

from app.api.routes import router as triage_router
from app.auth.routes import router as auth_router
from app.auth.middleware import LocalSessionMiddleware

app = FastAPI(
    title="MediFlow API",
    description="API de triaje clínico inteligente con OCI y LLM",
    version="1.0.0",
    debug=runtime_settings.DEBUG
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8080",
        "http://localhost:8080",
        "https://desktop-edilanti.tailf48a22.ts.net:10000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["X-Document-ID"],
)
# Agregado por Edil: la sesión de MediFlow identifica al usuario incluso al
# ejecutar Uvicorn directamente. Tailscale solamente transporta la conexión.
app.add_middleware(LocalSessionMiddleware)

@app.exception_handler(ReviewValidationError)
async def review_validation_handler(request: Request, exc: ReviewValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )

@app.exception_handler(DuplicateReviewError)
async def duplicate_review_handler(request: Request, exc: DuplicateReviewError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )

@app.exception_handler(ReviewNotFoundError)
async def review_not_found_handler(request: Request, exc: ReviewNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )

@app.exception_handler(OCITimeoutError)
async def oci_timeout_handler(request: Request, exc: OCITimeoutError):
    return JSONResponse(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        content={"detail": str(exc)},
    )

@app.exception_handler(OCIPersistenceError)
async def oci_persistence_handler(request: Request, exc: OCIPersistenceError):
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"detail": str(exc)},
    )

app.include_router(triage_router)
app.include_router(auth_router)

@app.get("/")
def health_check():
    return {"status": "ok", "app": "MediFlow Backend", "environment": runtime_settings.ENVIRONMENT}
