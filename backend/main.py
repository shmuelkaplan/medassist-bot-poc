from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from backend.models import ClinicalNote
from backend.logger import setup_logger
from backend.database import db
from backend.index_engine import query_patient_records, generate_basic_summary, extract_medical_tags, generate_clinical_snapshot
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
logger = setup_logger(__name__)

app = FastAPI(
    title="Medical Assistant Logic Tier",
    description="Backend orchestrator routing requests to Gemini and Firestore.",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://medassist-bot-poc.streamlit.app"],  # In production, Streamlit URL here
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
def submit_clinical_note(note: dict): # Using dict to match your current Streamlit payload
    logger.info(f"Received new note for patient {note.get('patient_id')}")
    try:
        # 1. INTERCEPT: Run the raw text through the AI Extractor
        #extracted_tags = extract_medical_tags(note.get("note_content", ""))
        #note["tags"] = extracted_tags
        #logger.info(f"AI extracted tags: {extracted_tags}")
        
        # 2. SAVE: Push the enriched data to Firestore
        db.collection("clinical_notes").add(note)
        return {"message": "Note saved and AI extraction complete."}
    except Exception as e:
        logger.error(f"Failed to save note: {e}")
        raise HTTPException(status_code=500, detail="Database insertion failed.")


# --- 1. Model for Updating a Note ---
class NoteUpdate(BaseModel):
    note_content: str

# --- 2. The Edit Endpoint ---
@app.put("/notes/{document_id}")
def update_clinical_note(document_id: str, update_data: NoteUpdate) -> dict:
    """
    Updates the text content of an existing clinical note in Firestore.
    """
    logger.info(f"Received update request for document: {document_id}")
    try:
        doc_ref = db.collection("clinical_notes").document(document_id)
        
        # Verify the document exists before updating
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="Note not found.")
            
        # Perform the update
        doc_ref.update({"note_content": update_data.note_content})
        
        logger.info(f"Successfully updated document: {document_id}")
        return {"message": "Note updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update note: {e}")
        raise HTTPException(status_code=500, detail="Failed to update database.")
    


@app.get("/patients/{patient_id}/timeline")
def get_patient_timeline(patient_id: str) -> dict:
    logger.info(f"Fetching chronological timeline for patient: {patient_id}")
    try:
        notes_ref = db.collection("clinical_notes").where("patient_id", "==", patient_id).stream()
        
        notes_list = []
        #analytics_counter = {} 
        
        for note in notes_ref:
            doc = note.to_dict()
            doc["document_id"] = note.id
            if "date_recorded" in doc and hasattr(doc["date_recorded"], "isoformat"):
                doc["date_recorded"] = doc["date_recorded"].isoformat()
            else:
                doc["date_recorded"] = str(doc.get("date_recorded", "Unknown Date"))
                
            # AGGREGATION LOGIC: Count every tag we find
           # for tag in doc.get("tags", []):
           #     analytics_counter[tag] = analytics_counter.get(tag, 0) + 1
                
            notes_list.append(doc)
            
        if not notes_list:
            raise HTTPException(status_code=404, detail="No clinical notes found for this patient.")
            
        notes_list.sort(key=lambda x: x.get("date_recorded", ""), reverse=True)
        
        # --- THE SNAPSHOT UPDATE ---
        # Stitch the text together for the AI to read
        history_text = "\n\n".join([f"Date: {n.get('date_recorded')} | Note: {n.get('note_content')}" for n in notes_list])
        
        # Call our new Senior Attending Physician prompt
        clinical_snapshot = generate_clinical_snapshot(history_text)
        
        return {
            "patient_id": patient_id,
            "snapshot": clinical_snapshot,  # Changed from 'summary' to 'snapshot'
            "recent_visits": notes_list[:3],
            "older_visits": notes_list[3:],
            #"analytics": analytics_counter 
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch timeline: {e}")
        raise HTTPException(status_code=500, detail="Database aggregation failed.")

# --- 1. The Pydantic Input Model ---
class ChatQuery(BaseModel):
    patient_id: str
    question: str

# --- 2. The Free-Text Query Endpoint ---
@app.post("/query/")
def ask_medical_assistant(query: ChatQuery) -> dict:
    """
    Retrieves a patient's full clinical history and uses the AI Reasoning engine 
    to answer free-text questions from the doctor.
    """
    logger.info(f"Received free-text query for Patient ID: {query.patient_id}")
    
    try:
        # Step 1: Fetch all notes from Firestore for this specific patient
        notes_ref = db.collection("clinical_notes").where("patient_id", "==", query.patient_id).stream()
        
        notes_list = []
        for note in notes_ref:
            doc = note.to_dict()
            
            # Format the datetime cleanly
            if "date_recorded" in doc and hasattr(doc["date_recorded"], "isoformat"):
                date_str = doc["date_recorded"].isoformat()
            else:
                date_str = str(doc.get("date_recorded", "Unknown Date"))
            
            # Create a structured string for the AI to read
            formatted_note = f"Date: {date_str} | Department: {doc.get('department')} | Note: {doc.get('note_content')}"
            notes_list.append(formatted_note)
            
        # If the patient has no records, short-circuit and return immediately
        if not notes_list:
            return {"answer": "I do not have any clinical notes on file for this patient to answer your question."}
            
        # Step 2: Stitch the history into a single, chronological text block
        full_history = "\n\n".join(notes_list)
        logger.info(f"Compiled {len(notes_list)} notes for reasoning context.")
        
        # Step 3: Pass to our Custom Gemini Reasoning Loop (Phase 1: Index, Phase 2: Reason)
        ai_response = query_patient_records(query.question, full_history)
        
        # Step 4: Return the answer matching the Streamlit UI's expectation
        return {"answer": ai_response}
        
    except Exception as e:
        logger.error(f"Failed to process AI query: {e}")
        raise HTTPException(status_code=500, detail="Failed to process medical query.")


