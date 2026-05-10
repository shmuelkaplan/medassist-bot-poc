from fastapi import FastAPI
from dotenv import load_dotenv
from backend.models import ClinicalNote
# Load environment variables from the .env file on startup
load_dotenv()

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
async def submit_clinical_note(note: ClinicalNote) -> dict:
    """
    Receive and validate a new clinical note from the Presentation Tier.
    
    Args:
        note (ClinicalNote): The validated clinical note payload.
        
    Returns:
        dict: A confirmation message and the echoed data.
    """
    return {
        "message": "Note successfully validated and received.",
        "data": note.model_dump()
    }