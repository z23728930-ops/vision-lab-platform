from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .core.config import settings
from .api.routers import auth, users, datasets, processing, hardware, models, inference, annotations, assistant

app = FastAPI(
    title="Defect Detection Backend API",
    description="API for defect detection and image processing platform.",
    version="0.1.0",
)

FRONTEND_ORIGINS = [
    "http://localhost",
    "http://localhost:5173",
    "http://127.0.0.1",
    "http://127.0.0.1:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

project_root = Path(__file__).parent.parent
uploads_directory = project_root / settings.UPLOADS_DIR
uploads_directory.mkdir(parents=True, exist_ok=True)
app.mount("/static_uploads", StaticFiles(directory=str(uploads_directory)), name="static_uploads")

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(datasets.router, prefix="/api/v1/datasets", tags=["Datasets"])
app.include_router(processing.router, prefix="/api/v1/processing", tags=["Processing"])
app.include_router(hardware.router, prefix="/api/v1/hardware", tags=["Hardware"])
app.include_router(models.router, prefix="/api/v1/models", tags=["Models"])
app.include_router(inference.router, prefix="/api/v1/inference", tags=["Inference"])
app.include_router(annotations.router, prefix="/api/v1/annotations", tags=["Annotations"])
app.include_router(assistant.router, prefix="/api/v1/assistant", tags=["AI Assistant"])


@app.get("/")
async def read_root():
    return {"message": "Welcome to the Defect Detection API!"}
