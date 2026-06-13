
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import List, Optional

class ClinicalNote(BaseModel):
    patient_id: str = Field(..., description="Unique identifier for the patient")
    doctor_id: str = Field(..., description="Unique identifier for the attending doctor")
    
    department: str = Field(default="General", description="The medical department submitting the note")
    
    date_recorded: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), 
        description="Timestamp of the note"
    )
    note_content: str = Field(..., min_length=10, description="The raw unstructured clinical text")
    tags: Optional[List[str]] = Field(default=[], description="Optional medical keywords or categories")