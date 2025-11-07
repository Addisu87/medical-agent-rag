from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    JSON,
    Boolean,
    Float,
    Enum,
    ForeignKey,
    Integer,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone
import enum

Base = declarative_base()


class TranscriptionStatus(enum.Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MedicalNoteType(enum.Enum):
    CONSULTATION = "consultation"
    FOLLOW_UP = "follow_up"
    EMERGENCY = "emergency"
    ROUTINE_CHECK = "routine_check"


class UrgencyLevel(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EMERGENCY = "emergency"


class Patient(Base):
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(DateTime, nullable=False)
    gender = Column(String(20))
    phone = Column(String(20))
    email = Column(String(100))
    medical_record_number = Column(String(50), unique=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    # Relationships
    transcriptions = relationship("Transcription", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    specialization = Column(String(100))
    license_number = Column(String(50), unique=True)
    phone = Column(String(20))
    email = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    transcriptions = relationship("Transcription", back_populates="doctor")
    appointments = relationship("Appointment", back_populates="doctor")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=30)
    status = Column(String(20), default="scheduled")  # scheduled, completed, cancelled
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    # Relationships
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    transcriptions = relationship("Transcription", back_populates="appointment")


class Transcription(Base):
    __tablename__ = "transcriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id"))

    # Audio metadata
    audio_file_path = Column(String(500))
    audio_duration = Column(Float)  # in seconds
    file_size = Column(Integer)  # in bytes

    # Transcription data
    raw_text = Column(Text)
    status = Column(Enum(TranscriptionStatus), default=TranscriptionStatus.PROCESSING)
    confidence_score = Column(Float)  # STT confidence 0-1
    language = Column(String(10), default="en")

    # Medical notes (structured JSON)
    medical_notes = Column(JSON)  # Stores the structured medical summary
    note_type = Column(Enum(MedicalNoteType), default=MedicalNoteType.CONSULTATION)
    urgency_level = Column(Enum(UrgencyLevel), default=UrgencyLevel.LOW)

    # LiveKit session data (for real-time transcriptions)
    live_session_id = Column(String(100))
    room_name = Column(String(100))

    # Timestamps
    processed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    # Relationships
    patient = relationship("Patient", back_populates="transcriptions")
    doctor = relationship("Doctor", back_populates="transcriptions")
    appointment = relationship("Appointment", back_populates="transcriptions")
    terminology_validations = relationship(
        "TerminologyValidation", back_populates="transcription"
    )

class MedicalSummary(Base):
    __tablename__ = "medical_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transcription_id = Column(
        UUID(as_uuid=True), ForeignKey("transcriptions.id"), nullable=False
    )

    # Structured summary fields
    symptoms = Column(JSON)  # List of symptoms with details
    diagnoses = Column(JSON)  # List of diagnoses
    medications = Column(JSON)  # List of prescribed medications
    procedures = Column(JSON)  # List of medical procedures
    recommendations = Column(JSON)  # List of recommendations
    follow_up_required = Column(Boolean, default=False)
    follow_up_date = Column(DateTime)
    clinical_summary = Column(Text)

    # Quality metrics
    summary_quality_score = Column(Float)
    completeness_score = Column(Float)

    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    # Relationships
    transcription = relationship("Transcription")