from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from typing import List, Optional, Dict, Any
from app.models.db_models import (
    Transcription, Patient, Doctor, Appointment, 
    TerminologyValidation, MedicalSummary, TranscriptionStatus
)
from app.models.schemas import TranscriptionCreate, TranscriptionResponse
import uuid
from datetime import datetime
import logfire


class DatabaseService:
    def __init__(self, db: Session):
        self.db = db
    
    # Transcription Operations
    async def create_transcription(self, transcription_data: TranscriptionCreate) -> Transcription:
        with logfire.span('create_transcription'):
            db_transcription = Transcription(
                id=uuid.uuid4(),
                patient_id=uuid.UUID(transcription_data.patient_id),
                doctor_id=uuid.UUID(transcription_data.doctor_id),
                appointment_id=uuid.UUID(transcription_data.appointment_id) if transcription_data.appointment_id else None,
                audio_file_path=transcription_data.audio_file_path,
                audio_duration=transcription_data.audio_duration,
                language=transcription_data.language,
                status=TranscriptionStatus.PROCESSING,
                created_at=datetime.utcnow()
            )
            
            self.db.add(db_transcription)
            self.db.commit()
            self.db.refresh(db_transcription)
            
            logfire.info(f"Created transcription record: {db_transcription.id}")
            return db_transcription
    
    async def get_transcription(self, transcription_id: str) -> Optional[Transcription]:
        with logfire.span('get_transcription'):
            return self.db.query(Transcription).filter(Transcription.id == uuid.UUID(transcription_id)).first()
    
    async def update_transcription(
        self, 
        transcription_id: str, 
        transcript_text: str = None,
        medical_notes: Dict[str, Any] = None,
        status: str = None,
        confidence_score: float = None
    ) -> Optional[Transcription]:
        try:
            transcription = await self.get_transcription(transcription_id)
            if not transcription:
                return None
            
            if transcript_text is not None:
                transcription.raw_text = transcript_text
            if medical_notes is not None:
                transcription.medical_notes = medical_notes
            if status is not None:
                transcription.status = TranscriptionStatus(status)
            if confidence_score is not None:
                transcription.confidence_score = confidence_score
            
            transcription.processed_at = datetime.utcnow()
            transcription.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(transcription)
            
            logfire.info(f"Updated transcription: {transcription_id}")
            return transcription
            
        except Exception as e:
            self.db.rollback()
            logfire.error(f"Failed to update transcription {transcription_id}: {e}")
            raise
    
    async def get_patient_transcriptions(self, patient_id: str) -> List[Transcription]:
        return (
            self.db.query(Transcription)
            .filter(Transcription.patient_id == uuid.UUID(patient_id))
            .order_by(desc(Transcription.created_at))
            .all()
        )
    
    async def get_doctor_transcriptions(self, doctor_id: str) -> List[Transcription]:
        return (
            self.db.query(Transcription)
            .filter(Transcription.doctor_id == uuid.UUID(doctor_id))
            .order_by(desc(Transcription.created_at))
            .all()
        )
    
    # Patient Operations
    async def get_patient(self, patient_id: str) -> Optional[Patient]:
        return self.db.query(Patient).filter(Patient.id == uuid.UUID(patient_id)).first()
    
    async def create_patient(self, patient_data: Dict[str, Any]) -> Patient:
        try:
            db_patient = Patient(
                id=uuid.uuid4(),
                **patient_data
            )
            
            self.db.add(db_patient)
            self.db.commit()
            self.db.refresh(db_patient)
            return db_patient
            
        except Exception as e:
            self.db.rollback()
            logfire.error(f"Failed to create patient: {e}")
            raise
    
    # Terminology Validation Operations
    async def save_terminology_validations(
        self, 
        transcription_id: str, 
        validations: List[Dict[str, Any]]
    ) -> List[TerminologyValidation]:
        try:
            db_validations = []
            for validation in validations:
                db_validation = TerminologyValidation(
                    id=uuid.uuid4(),
                    transcription_id=uuid.UUID(transcription_id),
                    original_term=validation['term'],
                    validated_term=validation.get('validated_term'),
                    is_medical=validation['is_medical'],
                    confidence=validation['confidence'],
                    category=validation.get('category'),
                    suggested_correction=validation.get('suggested_correction'),
                    created_at=datetime.utcnow()
                )
                db_validations.append(db_validation)
                self.db.add(db_validation)
            
            self.db.commit()
            
            for validation in db_validations:
                self.db.refresh(validation)
            
            logfire.info(f"Saved {len(db_validations)} terminology validations for transcription {transcription_id}")
            return db_validations
            
        except Exception as e:
            self.db.rollback()
            logfire.error(f"Failed to save terminology validations: {e}")
            raise
    
    # Medical Summary Operations
    async def save_medical_summary(self, transcription_id: str, summary_data: Dict[str, Any]) -> MedicalSummary:
        try:
            db_summary = MedicalSummary(
                id=uuid.uuid4(),
                transcription_id=uuid.UUID(transcription_id),
                symptoms=summary_data.get('symptoms', []),
                diagnoses=summary_data.get('diagnoses', []),
                medications=summary_data.get('medications', []),
                procedures=summary_data.get('procedures', []),
                recommendations=summary_data.get('recommendations', []),
                follow_up_required=summary_data.get('follow_up_required', False),
                follow_up_date=summary_data.get('follow_up_date'),
                clinical_summary=summary_data.get('summary', ''),
                summary_quality_score=summary_data.get('quality_score', 0.0),
                completeness_score=summary_data.get('completeness_score', 0.0),
                created_at=datetime.utcnow()
            )
            
            self.db.add(db_summary)
            self.db.commit()
            self.db.refresh(db_summary)
            
            logfire.info(f"Saved medical summary for transcription {transcription_id}")
            return db_summary
            
        except Exception as e:
            self.db.rollback()
            logfire.error(f"Failed to save medical summary: {e}")
            raise
    
    # Analytics and Reporting
    async def get_transcription_stats(self, doctor_id: str = None, days: int = 30) -> Dict[str, Any]:
        query = self.db.query(Transcription)
        
        if doctor_id:
            query = query.filter(Transcription.doctor_id == uuid.UUID(doctor_id))
        
        # Filter by date range
        start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = start_date.replace(day=start_date.day - days)
        query = query.filter(Transcription.created_at >= start_date)
        
        total = query.count()
        completed = query.filter(Transcription.status == TranscriptionStatus.COMPLETED).count()
        failed = query.filter(Transcription.status == TranscriptionStatus.FAILED).count()
        
        avg_confidence = self.db.query(
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