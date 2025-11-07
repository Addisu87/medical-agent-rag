import logging
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    inference,
    metrics,
)
from livekit.plugins import silero, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from app.agents.medical_summarizer import MedicalSummarizer
from app.agents.medical_transcriber import MedicalTranscriber

logger = logging.getLogger("medical-transcriber")

class MedicalTranscriptionAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""
            You are a medical transcription assistant. Focus on accurate transcription 
            and real-time summarization of medical conversations.
            """
        )

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()
    proc.userdata["summarizer"] = MedicalSummarizer()
    proc.userdata["transcriber"] = MedicalTranscriber()

async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}
    
    # Initialize services
    summarizer = ctx.proc.userdata["summarizer"]
    transcriber = ctx.proc.userdata["transcriber"]
    db_service = ctx.proc.userdata["db_service"]
    
    # Create session
    session = AgentSession(
        stt=inference.STT(model="assemblyai/universal-streaming", language="en"),
        llm=inference.LLM(model="openai/gpt-4"),
        tts=inference.TTS(model="cartesia/sonic-3"),
        vad=ctx.proc.userdata["vad"],
        turn_detection=MultilingualModel(),
        preemptive_generation=True
    )
    
    # Metrics collection
    usage_collector = metrics.UsageCollector()
    
    @session.on("metrics_collected")
    def _on_metrics_collected(ev):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)
    
    # Handle transcriptions
    @session.on("transcription_final")
    async def handle_transcription(event):
        transcript = event.result.text
        if not transcript:
            return
        
        logger.info(f"Transcription received: {transcript}")
        
        # Generate medical notes
        medical_notes = await summarizer.generate_medical_notes(transcript)
        
        # Store in database
        await db_service.save_transcription(
            transcript_text=transcript,
            medical_notes=medical_notes,
            room_name=ctx.room.name
        )
        
        logger.info(f"Medical notes generated and stored: {medical_notes}")
    
    # Start session
    await session.start(
        agent=MedicalTranscriptionAgent(),
        room=ctx.room,
        room_input_options={
            "noise_cancellation": noise_cancellation.BVC()
        }
    )

def run_agent():
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))

if __name__ == "__main__":
    run_agent()