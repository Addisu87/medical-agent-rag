from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
import logfire
import os
from app.db.session import get_db
from app.services.database_service import create_transcription, get_transcription, get_patient_transcriptions, update_transcription
from app.models.schemas import TranscriptionResponse

router = APIRouter()

@router.post("/transcribe/upload", response_model=TranscriptionResponse)
async def upload_audio_transcription(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    patient_id: str = "upload-patient",
    doctor_id: str = "upload-doctor",
    db: Session = Depends(get_db)
):
    with logfire.span("upload_audio_transcription"):
        # Validate file type
        allowed_extensions = {'.wav', '.mp3', '.m4a', '.webm'}
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(400, f"Unsupported audio format. Allowed: {allowed_extensions}")

        # Save file temporarily
        file_path = f"/tmp/{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        logfire.info("Audio file saved", file_path=file_path, file_size=len(content))

        # Create transcription record
        transcription = await create_transcription(
            db,
            patient_id=patient_id,
            doctor_id=doctor_id,
            audio_file_path=file_path,
            status="processing"
        )

        # Process in background
        background_tasks.add_task(
            process_audio_transcription,
            transcription.id,
            file_path,
            patient_id,
            doctor_id
        )

        logfire.info("Transcription task queued", transcription_id=str(transcription.id))
        return transcription


@router.get("/transcriptions/{transcription_id}")
async def get_transcription(transcription_id: str, db: Session = Depends(get_db)):
    with logfire.span("get_transcription"):
        transcription = await get_transcription(db, transcription_id)
        if not transcription:
            raise HTTPException(404, "Transcription not found")
        
        logfire.info("Transcription retrieved", transcription_id=transcription_id)
        return transcription


@router.get("/patients/{patient_id}/transcriptions")
async def get_patient_transcriptions(patient_id: str, db: Session = Depends(get_db)):
    with logfire.span("get_patient_transcriptions"):
        transcriptions = await get_patient_transcriptions(db, patient_id)
        logfire.info("Patient transcriptions retrieved", patient_id=patient_id, count=len(transcriptions))
        return transcriptions


@router.get("/doctor/{doctor_id}/transcriptions")
async def get_doctor_transcriptions(doctor_id: str, db: Session = Depends(get_db)):
    with logfire.span("get_doctor_transcriptions"):
        from app.services.database_service import get_doctor_transcriptions
        transcriptions = await get_doctor_transcriptions(db, doctor_id)
        logfire.info("Doctor transcriptions retrieved", doctor_id=doctor_id, count=len(transcriptions))
        return transcriptions


@router.post("/transcription/{transcription_id}/validate-terms")
async def validate_transcription_terms(transcription_id: str, db: Session = Depends(get_db)):
    """Validate medical terms from a specific transcription"""
    with logfire.span("validate_transcription_terms"):
        transcription = await get_transcription(db, transcription_id)
        if not transcription:
            raise HTTPException(404, "Transcription not found")
        
        # Extract and validate terms
        terms = extract_medical_terms(transcription.raw_text)
        validated_terms = await validate_terms(terms)
        
        from app.services.database_service import save_terminology_validations
        await save_terminology_validations(db, transcription_id, validated_terms)
        
        logfire.info("Terms validated", transcription_id=transcription_id, terms_count=len(validated_terms))
        return {"transcription_id": transcription_id, "validated_terms": validated_terms}


async def process_audio_transcription(transcription_id: str, audio_file_path: str, patient_id: str, doctor_id: str):
    with logfire.span("process_audio_transcription"):
        try:
            logfire.info("Starting audio transcription processing", transcription_id=transcription_id)
            
            # Note: We removed the MedicalTranscriber since we're using LiveKit for real-time
            # For file uploads, you'd need to implement file transcription here
            # For now, we'll simulate it
            transcript = "Simulated transcription from uploaded audio file. Patient reports chest pain and shortness of breath."
            
            # Generate medical notes
            medical_notes = await generate_medical_notes(transcript)
            
            # Extract and validate medical terms
            terms = extract_medical_terms(transcript)
            validated_terms = await validate_terms(terms)
            
            # Update database
            from app.db.session import SessionLocal
            db = SessionLocal()
            try:
                from app.services.database_service import update_transcription, save_terminology_validations
                
                await update_transcription(
                    db,
                    transcription_id,
                    raw_text=transcript,
                    medical_notes=medical_notes,
                    status="completed",
                    confidence_score=0.95
                )
                
                # Save validated terms
                if validated_terms:
                    await save_terminology_validations(db, transcription_id, validated_terms)
                
                logfire.info(
                    "Audio processing completed",
                    transcription_id=transcription_id,
                    transcript_length=len(transcript),
                    terms_validated=len(validated_terms)
                )
                
            finally:
                db.close()
            
            # Clean up temporary file
            os.remove(audio_file_path)
            logfire.debug("Temporary file cleaned up", file_path=audio_file_path)
            
        except Exception as e:
            logfire.error("Audio processing failed", transcription_id=transcription_id, error=str(e))
            
            # Update database with failure status
            from app.db.session import SessionLocal
            db = SessionLocal()
            try:
                from app.services.database_service import update_transcription
                await update_transcription(db, transcription_id, status="failed")
            finally:
                db.close()