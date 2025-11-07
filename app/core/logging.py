import logfire
from app.core.config import settings


# Simple one-time configuration
def setup_logfire():
    """Configure Logfire with minimal settings"""
    logfire.configure(
        service_name="medical-transcription-ai",
        service_version="1.0.0",
        token=settings.LOGFIRE_TOKEN,
        send_to_logfire=bool(settings.LOGFIRE_TOKEN),
    )
    logfire.instrument_pydantic_ai()

    if settings.LOGFIRE_TOKEN:
        logfire.info("Logfire configured with cloud integration")
    else:
        logfire.info("Logfire running in local mode")


# Auto-configure on import
setup_logfire()
