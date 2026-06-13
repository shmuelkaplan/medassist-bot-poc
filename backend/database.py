import os 
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
from backend.logger import setup_logger

load_dotenv()
logger = setup_logger(__name__)

def  get_db_client():
    """
    Initializes and returns a connection to Google Cloud Firestore.
    Uses the Singleton pattern to prevent initializing the app multiple times.
    
    Returns:
        google.cloud.firestore.Client: The active Firestore database client.
        
    Raises:
        FileNotFoundError: If the Firebase credentials JSON file is missing.
    """
    if not firebase_admin._apps:
        cred_path = os.getenv('FIREBASE_CREDENTIALS')
        
        if not cred_path:
            raise FileNotFoundError(
                f"CRITICAL ERROR: Firebase credentials not found at {cred_path}. "
                "Ensure the JSON file is in the secrets/ directory."
            )
        try:
            logger.info("Initializing Firebase Admin SDK")
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase client created succesfully")
        except Exception as e:
            logger.error(f"Faield to connect to Firebase: {e}")
    return firestore.client()

db = get_db_client()