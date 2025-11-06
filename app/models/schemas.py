from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class TranscriptionStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class MedicalNoteType(str, Enum):
    CONSULTATION = "consultation"
    FOLLOW_UP = "follow_up"
    EMERGENCY = "emergency"
    ROUTINE_CHECK = "routine_check"

class TranscriptionBase(BaseModel):
    patient_id: str
    doctor_id: str
    appointment_id: Optional[str]
    audio_duration: Optional[float]
    language: str = "en"

class TranscriptionCreate(TranscriptionBase):
    audio_file_path: Optional[str]
    live_session_id: Optional[str]

class TranscriptionResponse(TranscriptionBase):
    id: str
    status: TranscriptionStatus
    raw_text: Optional[str]
    medical_notes: Optional[Dict[str, Any]]
    confidence_score: Optional[float]
    processed_at: Optional[datetime]
    created_at: datetime

class MedicalNote(BaseModel):
    symptoms: List[str]
    diagnoses: List[str]
    medications: List[Dict[str, str]]
    procedures: List[str]
    recommendations: List[str]
    follow_up_required: bool
    follow_up_date: Optional[str]
    urgency_level: str  # low, medium, high, emergency
    summary: str

class TerminologyValidation(BaseModel):
    term: str
    is_medical: bool
    confidence: float
    suggested_correction: Optional[str]
    category: Optional[str]