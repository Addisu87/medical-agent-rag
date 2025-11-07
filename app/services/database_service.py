from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional, Dict, Any
from app.db.models import Transcription, MedicalSummary, TranscriptionStatus, Patient
import uuid
from datetime import datetime, timezone
import logfire

# Transcription Operations
async def create_transcription(db: Session, **transcription_data) -> Transcription:
    with logfire.span("create_transcription"):
        # Create transcription with defaults
        transcription_dict = {
            "id": uuid.uuid4(),
            "status": TranscriptionStatus.COMPLETED,
            "created_at": datetime.now(timezone.utc),
            "processed_at": datetime.now(timezone.utc),
            **transcription_data  # Merge all provided data
        }
        
        # Convert string IDs to UUID if needed
        for field in ['patient_id', 'doctor_id', 'appointment_id']:
            if field in transcription_dict and transcription_dict[field]:
                transcription_dict[field] = uuid.UUID(transcription_dict[field])

        db_transcription = Transcription(**transcription_dict)
        db.add(db_transcription)
        db.commit()
        db.refresh(db_transcription)

        logfire.info("Created transcription", transcription_id=str(db_transcription.id))
        return db_transcription

async def get_transcription(db: Session, transcription_id: str) -> Optional[Transcription]:
    with logfire.span("get_transcription"):
        return db.query(Transcription).filter(Transcription.id == uuid.UUID(transcription_id)).first()

async def update_transcription(db: Session, transcription_id: str, **update_fields) -> Optional[Transcription]:
    try:
        transcription = await get_transcription(db, transcription_id)
        if not transcription:
            return None

        # Update all fields at once
        for field, value in update_fields.items():
            if value is not None:
                setattr(transcription, field, value)

        transcription.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(transcription)

        logfire.info("Updated transcription", transcription_id=transcription_id)
        return transcription

    except Exception as e:
        db.rollback()
        logfire.error("Failed to update transcription", transcription_id=transcription_id, error=str(e))
        raise

async def get_patient_transcriptions(db: Session, patient_id: str) -> List[Transcription]:
    return (
        db.query(Transcription)
        .filter(Transcription.patient_id == uuid.UUID(patient_id))
        .order_by(desc(Transcription.created_at))
        .all()
    )
async def get_doctor_transcriptions(db: Session, doctor_id: str) -> List[Transcription]:
    with logfire.span("get_doctor_transcriptions"):
        return (
            db.query(Transcription)
            .filter(Transcription.doctor_id == uuid.UUID(doctor_id))
            .order_by(desc(Transcription.created_at))
            .all()
        )

# Patient Operations
async def get_patient(db: Session, patient_id: str) -> Optional[Patient]:
    return db.query(Patient).filter(Patient.id == uuid.UUID(patient_id)).first()


async def create_patient(db: Session, patient_data: Dict[str, Any]) -> Patient:
    try:
        patient_dict = patient_data.copy()
        patient_dict['id'] = uuid.uuid4()
        
        db_patient = Patient(**patient_dict)
        
        db.add(db_patient)
        db.commit()
        db.refresh(db_patient)
        return db_patient
        
    except Exception as e:
        db.rollback()
        logfire.error(f"Failed to create patient: {e}")
        raise

async def save_medical_summary(db: Session, transcription_id: str, **summary_data) -> MedicalSummary:
    with logfire.span("save_medical_summary"):
        summary_dict = {
            "id": uuid.uuid4(),
            "transcription_id": uuid.UUID(transcription_id),
            "created_at": datetime.now(timezone.utc),
            **summary_data  # Merge all summary data
        }

        db_summary = MedicalSummary(**summary_dict)
        db.add(db_summary)
        db.commit()
        db.refresh(db_summary)

        logfire.info("Saved medical summary", transcription_id=transcription_id)
        return db_summary
    