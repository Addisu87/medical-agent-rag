import logfire
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.logging import setup_logfire
from app.api.routes import router as api_router
from app.db.session import init_db
import uvicorn


# Configure logging
setup_logfire()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logfire.info("Application starting up")
    init_db()
    yield
    # Shutdown
    logfire.info("Application shutting down")


app = FastAPI(
    title="Medical Transcription AI",
    description="AI-powered medical conversation transcription and summarization",
    version="1.0.0",
    lifespan=lifespan,
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.get("/health")
async def health_check():
    logfire.info("Health check called")
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
