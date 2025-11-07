from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional, Dict, Any
from app.db.models import (
    Transcription, Patient, Doctor, Appointment, 
    TerminologyValidation, MedicalSummary, TranscriptionStatus
)
from app.models.schemas import TranscriptionCreate
import uuid
from datetime import datetime, timezone
import logfire


# Transcription Operations
async def create_transcription(db: Session, transcription_data: TranscriptionCreate) -> Transcription:
    with logfire.span('create_transcription'):
        # Use model_dump() to get all data, then modify specific fields
        transcription_dict = transcription_data.model_dump()
        transcription_dict.update({
            'id': uuid.uuid4(),
            'patient_id': uuid.UUID(transcription_dict['patient_id']),
            'doctor_id': uuid.UUID(transcription_dict['doctor_id']),
            'appointment_id': uuid.UUID(transcription_dict['appointment_id']) if transcription_dict.get('appointment_id') else None,
            'status': TranscriptionStatus.PROCESSING,
            'created_at': datetime.now(timezone.utc)
        })
        
        db_transcription = Transcription(**transcription_dict)
        
        db.add(db_transcription)
        db.commit()
        db.refresh(db_transcription)
        
        logfire.info(f"Created transcription record: {db_transcription.id}")
        return db_transcription


async def get_transcription(db: Session, transcription_id: str) -> Optional[Transcription]:
    with logfire.span('get_transcription'):
        return db.query(Transcription).filter(Transcription.id == uuid.UUID(transcription_id)).first()


async def update_transcription(
    db: Session,
    transcription_id: str, 
    **update_fields
) -> Optional[Transcription]:
    try:
        transcription = await get_transcription(db, transcription_id)
        if not transcription:
            return None
        
        # Update fields dynamically
        for field, value in update_fields.items():
            if value is not None:
                if field == 'status':
                    setattr(transcription, field, TranscriptionStatus(value))
                else:
                    setattr(transcription, field, value)
        
        transcription.processed_at = datetime.now(timezone.utc)
        transcription.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(transcription)
        
        logfire.info(f"Updated transcription: {transcription_id}")
        return transcription
        
    except Exception as e:
        db.rollback()
        logfire.error(f"Failed to update transcription {transcription_id}: {e}")
        raise


async def get_patient_transcriptions(db: Session, patient_id: str) -> List[Transcription]:
    return (
        db.query(Transcription)
        .filter(Transcription.patient_id == uuid.UUID(patient_id))
        .order_by(desc(Transcription.created_at))
        .all()
    )


async def get_doctor_transcriptions(db: Session, doctor_id: str) -> List[Transcription]:
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


# Terminology Validation Operations
async def save_terminology_validations(
    db: Session,
    transcription_id: str, 
    validations: List[Dict[str, Any]]
) -> List[TerminologyValidation]:
    try:
        db_validations = []
        for validation in validations:
            validation_data = {
                'id': uuid.uuid4(),
                'transcription_id': uuid.UUID(transcription_id),
                'original_term': validation['term'],
                'validated_term': validation.get('validated_term'),
                'is_medical': validation['is_medical'],
                'confidence': validation['confidence'],
                'category': validation.get('category'),
                'suggested_correction': validation.get('suggested_correction'),
                'created_at': datetime.now(timezone.utc)
            }
            
            db_validation = TerminologyValidation(**validation_data)
            db_validations.append(db_validation)
            db.add(db_validation)
        
        db.commit()
        
        for validation in db_validations:
            db.refresh(validation)
        
        logfire.info(f"Saved {len(db_validations)} terminology validations for transcription {transcription_id}")
        return db_validations
        
    except Exception as e:
        db.rollback()
        logfire.error(f"Failed to save terminology validations: {e}")
        raise


# Medical Summary Operations
async def save_medical_summary(db: Session, transcription_id: str, summary_data: Dict[str, Any]) -> MedicalSummary:
    try:
        summary_dict = {
            'id': uuid.uuid4(),
            'transcription_id': uuid.UUID(transcription_id),
            'symptoms': summary_data.get('symptoms', []),
            'diagnoses': summary_data.get('diagnoses', []),
            'medications': summary_data.get('medications', []),
            'procedures': summary_data.get('procedures', []),
            'recommendations': summary_data.get('recommendations', []),
            'follow_up_required': summary_data.get('follow_up_required', False),
            'follow_up_date': summary_data.get('follow_up_date'),
            'clinical_summary': summary_data.get('summary', ''),
            'summary_quality_score': summary_data.get('quality_score', 0.0),
            'completeness_score': summary_data.get('completeness_score', 0.0),
            'created_at': datetime.now(timezone.utc)
        }
        
        db_summary = MedicalSummary(**summary_dict)
        
        db.add(db_summary)
        db.commit()
        db.refresh(db_summary)
        
        logfire.info(f"Saved medical summary for transcription {transcription_id}")
        return db_summary
        
    except Exception as e:
        db.rollback()
        logfire.error(f"Failed to save medical summary: {e}")
        raise


# Analytics and Reporting
async def get_transcription_stats(db: Session, doctor_id: str, days: int = 30) -> Dict[str, Any]:
    query = db.query(Transcription)
    
    if doctor_id:
        query = query.filter(Transcription.doctor_id == uuid.UUID(doctor_id))
    
    # Filter by date range
    start_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = start_date.replace(day=start_date.day - days)
    query = query.filter(Transcription.created_at >= start_date)
    
    total = query.count()
    completed = query.filter(Transcription.status == TranscriptionStatus.COMPLETED).count()
    failed = query.filter(Transcription.status == TranscriptionStatus.FAILED).count()
    
    avg_confidence = db.query(
        func.avg(Transcription.confidence_score)
    ).filter(
        Transcription.status == TranscriptionStatus.COMPLETED
    ).scalar() or 0.0
    
    return {
        "total": total,
        "completed": completed,
        "failed": failed,
        "success_rate": (completed / total * 100) if total > 0 else 0,
        "average_confidence": float(avg_confidence),
        "period_days": days
    }