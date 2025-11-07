from pydantic import BaseModel
from typing import List, Dict
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
    appointment_id: str | None = None
    audio_duration: float | None = None
    language: str = "en"

class TranscriptionCreate(TranscriptionBase):
    audio_file_path: str | None = None
    live_session_id: str | None = None

class TranscriptionResponse(TranscriptionBase):
    id: str
    status: TranscriptionStatus
    raw_text: str | None = None
    medical_notes: str | None = None
    confidence_score: float | None = None
    processed_at: datetime
    created_at: datetime

class MedicalNote(BaseModel):
    symptoms: List[str]
    diagnoses: List[str]
    medications: List[Dict[str, str]]
    procedures: List[str]
    recommendations: List[str]
    follow_up_required: bool
    follow_up_date: str | None = None
    urgency_level: str  # low, medium, high, emergency
    summary: str

class TerminologyValidation(BaseModel):
    term: str
    is_medical: bool
    confidence: float
    suggested_correction: str | None = None
    category: str | None = None