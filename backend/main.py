from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from backend.models import ClinicalNote
from backend.logger import setup_logger
from backend.database import db

load_dotenv()
logger = setup_logger(__name__)

app = FastAPI(
    title="Medical Assistant Logic Tier",
    description="Backend orchestrator routing requests to Gemini and Firestore.",
    version="0.1.0"
)

@app.get("/health")
async def health_check() -> dict:
    """
    Perform a basic health check on the API gateway.
    
    Returns:
        dict: A JSON response indicating the server status.
    """
    return {"status": "healthy", "tier": "Logic"}


@app.post("/notes/")
def submit_clinical_note(note: ClinicalNote) -> dict:
    """
    Receive and validate a new clinical note from the Presentation Tier.
    
    Args:
        note (ClinicalNote): The validated clinical note payload.
        
    Returns:
        dict: A confirmation message and the echoed data.
    """
    logger.info(f"Recevied new Clinical Note with Patien ID: {note.patient_id}")

    try:
        # formathing the data from pydantic to dict
        note_data = note.model_dump()

        # writing the data to Firestore 
        collection_ref = db.collection("clinical_notes")
        update_time, doc_ref = collection_ref.add(note_data)

        logger.info(f"Succesfuly saved the note to Firestore with document ID: {doc_ref.id}")

        return {
            "message": "Note successfully validated and saved to database.",
            "document_id": doc_ref.id
        }
    except Exception as e:
        logger.error(f"Faield to save note to Firestore: {e}")
        raise HTTPException(status_code=500, detail="Database insertion faild")
    