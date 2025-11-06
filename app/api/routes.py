from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
import logfire
import os
from app.services.audio_service import AudioService
from app.services.database_service import DatabaseService
from app.models.schemas import TranscriptionResponse, TranscriptionCreate

router = APIRouter()
audio_service = AudioService()
db_service = DatabaseService()

@router.post("/transcribe/upload", response_model=TranscriptionResponse)
async def upload_audio_transcription(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    patient_id: str = None,
    doctor_id: str = None
):
    # Validate file type
    if not any(file.filename.endswith(ext) for ext in [".wav", ".mp3", ".m4a"]):
        raise HTTPException(400, "Unsupported audio format")
    
    # Save file temporarily
    file_path = f"/tmp/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    # Create transcription record
    transcription_data = TranscriptionCreate(
        patient_id=patient_id,
        doctor_id=doctor_id,
        audio_file_path=file_path
    )
    
    # Process in background
    transcription = await db_service.create_transcription(transcription_data)
    
    background_tasks.add_task(
        process_audio_transcription,
        transcription.id,
        file_path
    )
    
    return transcription

@router.get("/transcriptions/{transcription_id}")
async def get_transcription(transcription_id: str):
    transcription = await db_service.get_transcription(transcription_id)
    if not transcription:
        raise HTTPException(404, "Transcription not found")
    return transcription

@router.get("/patients/{patient_id}/transcriptions")
async def get_patient_transcriptions(patient_id: str):
    return await db_service.get_patient_transcriptions(patient_id)

async def process_audio_transcription(transcription_id: str, audio_file_path: str):
    try:
        # Transcribe audio
        transcriber = MedicalTranscriber()
        transcript = await transcriber.transcribe_audio(audio_file_path)
        
        # Generate medical notes
        summarizer = MedicalSummarizer()
        medical_notes = await summarizer.generate_medical_notes(transcript)
        
        # Update database
        await db_service.update_transcription(
            transcription_id,
            transcript_text=transcript,
            medical_notes=medical_notes,
            status="completed"
        )
        
        # Clean up temporary file
        os.remove(audio_file_path)
        
    except Exception as e:
        await db_service.update_transcription(
            transcription_id,
            status="failed"
        )
        logfire.error(f"Transcription processing failed: {e}")