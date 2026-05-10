from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone

class ClinicalNote(BaseModel):
    """
    Represents a single clinical note submitted by a doctor.
    This acts as the strict schema for incoming POST requests.
    """
    patient_id: str = Field(..., description="Unique identifier for the patient")
    doctor_id: str = Field(..., description="Unique identifier for the attending doctor")
    date_recorded: datetime = Field(default_factory=datetime.now(timezone.utc), description="Timestamp of the note")
    note_content: str = Field(..., min_length=10, description="The raw unstructured clinical text")
    tags: Optional[List[str]] = Field(default=[], description="Optional medical keywords or categories")