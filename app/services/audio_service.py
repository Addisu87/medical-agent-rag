import logfire
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
from app.agents.medical_summarizer import generate_medical_notes
from app.db.session import SessionLocal
from app.services.database_service import create_transcription

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
    logfire.info("VAD model loaded")

async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}
    
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
        if not event.result.text:
            return
        
        with logfire.span("handle_transcription"):
            transcript = event.result.text
            medical_notes = await generate_medical_notes(transcript)
        
            # Save to database
            db = SessionLocal()
            try:
                await create_transcription(
                    db,
                    patient_id="livekit-patient",
                    doctor_id="livekit-doctor",
                    raw_text=transcript,
                    medical_notes=medical_notes,
                    room_name=ctx.room.name
                )
                logfire.info("Medical transcription saved to records")
            except Exception as e:
                logfire.error("Failed to save transcription", error=str(e))
            finally:
                db.close()
            
            # Speak summary to user
            summary = medical_notes.get('summary', 'Key medical points noted.')
            await session.say(f"Medical summary: {summary}")
    
    await session.start(
        agent=MedicalTranscriptionAgent(),
        room=ctx.room,
        room_input_options={"noise_cancellation": noise_cancellation.BVC()}
    )

def run_agent():
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))

if __name__ == "__main__":
    run_agent()