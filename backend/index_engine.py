# backend/index_engine.py
import os
from google import genai
from dotenv import load_dotenv
from backend.logger import setup_logger
import json


logger = setup_logger(__name__)
load_dotenv()

def setup_ai_client() -> genai.Client:
    """Configures and returns the unified Google GenAI Client."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "":
        logger.critical("Valid Gemini API key missing.")
        raise ValueError("CRITICAL ERROR: GEMINI_API_KEY not configured.")
        
    # The new SDK uses a stateless Client object instead of global configuration
    client = genai.Client(api_key=api_key)
    logger.info("Google GenAI Client initialized successfully.")
    return client

# Instantiate the client
ai_client = setup_ai_client()

# Define the model we are using for reasoning
MODEL_ID = 'gemini-3-flash-preview'

def generate_patient_index(patient_history: str) -> str:
    """
    Phase 1 of PageIndex architecture: 
    Generates a structured hierarchical map (Table of Contents) of the patient's records.
    """
    logger.info("Generating chronological index for patient records...")
    
    prompt = f"""
    You are a medical data architect. Analyze the following patient history.
    Do not answer any questions. Your only job is to create a chronological 'Table of Contents' 
    mapping the patient's visits, departments, and major medical events.
    
    Patient History:
    {patient_history}
    
    Output a structured map.
    """
    try:
        # In the new SDK, we call generate_content on the client.models interface
        response = ai_client.models.generate_content(
            model=MODEL_ID, 
            contents=prompt
        )
        return response.text
    except Exception as e:
        logger.error(f"Failed to generate index: {e}")
        raise e

def query_patient_records(question: str, patient_history: str) -> str:
    """
    Phase 2 of PageIndex architecture:
    Uses the generated index to reason about where the answer lives, then extracts it.
    """
    logger.info(f"Processing clinical query: '{question}'")
    
    # 1. First, we dynamically generate the structural map
    index_map = generate_patient_index(patient_history)
    
    # 2. Then, we force Gemini to use that map to find the answer
    reasoning_prompt = f"""
    You are an expert Chief Medical Officer analyzing a patient file.
    
    Step 1: Review this structural map of the patient's history to locate relevant events.
    <index_map>
    {index_map}
    </index_map>
    
    Step 2: Review the full unstructured clinical text.
    <patient_history>
    {patient_history}
    </patient_history>
    
    Question: {question}
    
    Based ONLY on the provided text, answer the question. Cite the specific visit date or department in your answer.
    """
    
    try:
        response = ai_client.models.generate_content(
            model=MODEL_ID, 
            contents=reasoning_prompt
        )
        logger.info("Successfully executed reasoning loop.")
        return response.text
    except Exception as e:
        logger.error(f"Reasoning query failed: {e}")
        raise e


def generate_basic_summary(patient_history: str) -> str:
    """
    Generates a concise 2-3 sentence clinical summary of the patient's history.
    
    Args:
        patient_history (str): The compiled chronological text of all patient notes.
        
    Returns:
        str: A short AI-generated clinical summary.
    """
    logger.info("Generating automatic short basic summary...")
    
    prompt = f"""
    You are an expert triage nurse. Read the following patient history and provide a strict 
    2-3 sentence clinical summary. Highlight any chronic conditions and their most recent chief complaint.
    Summerize basic information such as Age, Marital status, Known deseases, Known allergies, and 
    additional information that is relavent to know for correct emergency treatment.   
    
    Patient History:
    {patient_history}
    """
    
    try:
        response = ai_client.models.generate_content(
            model=MODEL_ID, 
            contents=prompt
        )
        return response.text
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        return "Automatic summary currently unavailable."


def extract_medical_tags(note_text: str) -> list:
    """
    Reads a raw clinical note and extracts medical entities into a structured JSON array.
    """
    logger.info("Extracting structured medical entities from note...")
    
    prompt = f"""
    You are a medical data extraction algorithm. Read the following clinical note.
    Extract all medical conditions, medications, and symptoms, and any other information 
    that a docotor should know imediatly in emerhency cases and clinical data that give the picture 
    of the patient help.
    
    Return ONLY a valid JSON list of strings. Format each string exactly like this: "Category: Value".
    Do not include any other text or markdown formatting.
    
    Example Output: 
    ["Condition: Hypertension", "Medication: Amlodipine 5mg", "Symptom: Chest pain"]
    
    Clinical Note:
    {note_text}
    """
    
    try:
        response = ai_client.models.generate_content(
            model=MODEL_ID, 
            contents=prompt
        )
        
        # Safety filter: LLMs sometimes wrap JSON in markdown blockticks (```json ... ```)
        # We strip those out so Python's json.loads() doesn't crash.
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        
        return json.loads(clean_json)
    except Exception as e:
        logger.error(f"Failed to extract tags: {e}")
        # If the AI fails, return an empty list so the server doesn't crash
        return []

def generate_clinical_snapshot(history_text: str) -> dict:
    """
    Scans all unstructured clinical history documents and compiles a structured
    real-time snapshot for the analytics dashboard.
    """
    logger.info("Generating dynamic clinical snapshot dashboard via Gemini...")
    
    prompt = f"""
    You are a Senior Attending Physician handing off a patient to a medical colleague. 
    Your objective is to provide a comprehensive, real-time clinical picture so the receiving doctor immediately understands the patient's exact state, risks, and history.
    
    Analyze the clinical history below and extract ALL possible relevant clinical data. 
    Do not leave out any detail that would be critical for emergency care or long-term clinical understanding.
    
    Return ONLY a valid JSON object. You must include the core clinical keys below, but you are highly encouraged to dynamically invent and add new keys (e.g., "allergies", "vital_trends", "social_history", "critical_warnings", "surgical_history") if that data exists in the notes.
    
    Base JSON Schema:
    {{
        "current_clinical_picture": "A 2-3 sentence professional physician's summary of their overall state and stability.",
        "active_diagnoses": ["..."],
        "regular_medications": ["..."],
        "pending_tests_and_treatments": ["..."],
        "future_procedures": ["..."]
        // --- INVENT AND ADD ANY OTHER CLINICALLY RELEVANT KEYS BELOW ---
    }}
    
    Patient Clinical History:
    {history_text}
    """
    
    try:
        response = ai_client.models.generate_content(
            model=MODEL_ID, 
            contents=prompt
        )
        
        # Clean up any potential markdown formatting errors
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        logger.error(f"Failed to generate clinical snapshot: {e}")
        # Graceful fallback schema
        return {
            "active_diagnoses": [],
            "regular_medications": [],
            "current_treatment_status": "Error compiling status.",
            "pending_tests_and_treatments": [],
            "future_procedures": []
        }

# --- Local Testing Block ---
if __name__ == "__main__":
    mock_history = """
    2025-11-20 (General Practice): Patient complains of severe migraine and nausea for 3 days. Prescribed 400mg Ibuprofen and advised rest.
    2026-04-10 (Cardiology): Routine follow-up. Blood pressure slightly elevated at 135/85. No action taken.
    2026-05-15 (Annual Checkup): Patient reports migraines have stopped. Vitals normal.
    """
    
    question = "What medication was the patient prescribed for their migraines, and when did the migraines stop?"
    
    print("--- Executing Reasoning RAG (New SDK) ---")
    answer = query_patient_records(question, mock_history)
    print(f"\nAI Answer:\n{answer}")