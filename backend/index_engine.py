# backend/index_engine.py
import os
from google import genai
from dotenv import load_dotenv
from backend.logger import setup_logger
import json
import time 

logger = setup_logger(__name__)
load_dotenv()

# The system will try these active models in order from top to bottom
FALLBACK_MODELS = [
    "gemini-3.5-flash",        # Primary: State-of-the-art fast reasoning
    "gemini-2.5-flash",        # Fallback 1: Solid predecessor, excellent availability
    "gemini-3.1-flash-lite",   # Fallback 2: Ultra-fast 3-series workhorse
    "gemini-2.5-flash-lite"    # Fallback 3: Extremely lightweight, virtually never maxed out
]

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


def generate_patient_index(patient_history: str) -> str:
    """
    Phase 1 of PageIndex architecture: 
    Generates a structured hierarchical map (Table of Contents) of the patient's records.
    
    Architectural Update: Implements a Model Waterfall fallback loop to gracefully
    handle 503/429 traffic spikes from the primary LLM provider.
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
    
    # --- The Cascade Routing Loop ---
    for model_id in FALLBACK_MODELS:
        try:
            logger.info(f"Attempting to generate index map using model: {model_id}")
            
            # In the new SDK, we call generate_content on the client.models interface
            response = ai_client.models.generate_content(
                model=model_id, 
                contents=prompt
            )
            
            logger.info(f"Successfully generated index map using {model_id}.")
            return response.text
            
        except Exception as e:
            error_msg = str(e)
            
            # Catch Traffic/Server Errors
            if "503" in error_msg or "429" in error_msg:
                logger.warning(f"Server {model_id} is busy. Falling back to next model for index generation...")
                time.sleep(1)
                continue
            else:
                # If it's a structural error (like API keys), break the loop
                logger.error(f"Critical AI Error with {model_id} during index generation: {error_msg}")
                break
                
    # --- Ultimate Graceful Degradation ---
    # If the index fails to build, we return a fallback string. 
    # Phase 2 will receive this string and naturally fall back to reading the raw text.
    logger.error("All AI models failed to generate the patient index. Returning bypass string.")
    return "Index Generation Failed due to server load. Proceed to Phase 2 and read the raw patient history directly."


def query_patient_records(question: str, patient_history: str) -> str:
    """
    Phase 2 of PageIndex architecture:
    Uses the generated index to reason about where the answer lives, then extracts it.
    
    Architectural Update: Now implements a Model Waterfall fallback loop to gracefully
    handle 503/429 traffic spikes from the primary LLM provider.
    """
    logger.info(f"Processing clinical query: '{question}'")
    
    # 1. First, we dynamically generate the structural map
    index_map = generate_patient_index(patient_history)
    
    # 2. Then, we construct the reasoning prompt
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
    
    # 3. The Cascade Routing Loop
    for model_id in FALLBACK_MODELS:
        try:
            logger.info(f"Attempting reasoning query with model: {model_id}")
            
            response = ai_client.models.generate_content(
                model=model_id, 
                contents=reasoning_prompt
            )
            
            logger.info(f"Successfully executed reasoning loop using {model_id}.")
            return response.text
            
        except Exception as e:
            error_msg = str(e)
            
            # Catch Traffic/Server Errors
            if "503" in error_msg or "429" in error_msg:
                logger.warning(f"Server {model_id} is busy. Falling back to next model...")
                time.sleep(1)
                continue
            else:
                # If it's a structural error (like API keys), break the loop
                logger.error(f"Critical AI Error with {model_id}: {error_msg}")
                break
                
    # 4. Ultimate Graceful Degradation
    logger.error("All AI models failed or timed out during patient query.")
    return "System Warning: The AI reasoning engine is currently experiencing extreme global server demand. Please try again in a few minutes."




def generate_clinical_snapshot(history_text: str) -> dict:
    """
    Scans all unstructured clinical history documents and compiles a structured
    real-time snapshot for the analytics dashboard using a resilient model waterfall.
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
    }}
    
    Patient Clinical History:
    {history_text}
    """
    
    # --- 2. The Cascade Routing Loop ---
    for model_id in FALLBACK_MODELS:
        try:
            logger.info(f"Attempting JSON extraction with model: {model_id}")
            
            response = ai_client.models.generate_content(
                model=model_id, 
                contents=prompt
            )
            
            # Clean up any potential markdown formatting errors
            clean_json = response.text.replace("```json", "").replace("```", "").strip()
            parsed_data = json.loads(clean_json)
            
            logger.info(f"Success! Snapshot compiled using {model_id}")
            return parsed_data
            
        except Exception as e:
            error_msg = str(e)
            
            # Catch Traffic/Server Errors
            if "503" in error_msg or "429" in error_msg:
                logger.warning(f"Server {model_id} is busy. Falling back to next model...")
                time.sleep(1)
                continue
                
            # Catch JSON Parsing Errors (in case a fallback model hallucinated bad text)
            elif "Expecting value" in error_msg or "JSONDecodeError" in error_msg.__class__.__name__:
                logger.warning(f"Model {model_id} returned invalid JSON. Falling back to next model...")
                continue
                
            # For critical auth or code errors, break the loop immediately
            else:
                logger.error(f"Critical AI Error with {model_id}: {error_msg}")
                break
                
    # --- 3. The Ultimate Graceful Degradation ---
    # If the loop exhausts all models, return a safe schema so the Streamlit UI doesn't crash
    logger.error("All AI models failed or timed out. Returning safe fallback schema.")
    return {
        "current_clinical_picture": "System Warning: AI extraction is temporarily unavailable due to extreme global server demand. Please read raw notes below.",
        "active_diagnoses": [],
        "regular_medications": [],
        "pending_tests_and_treatments": [],
        "future_procedures": []
    }




'''
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
'''


'''
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

'''




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