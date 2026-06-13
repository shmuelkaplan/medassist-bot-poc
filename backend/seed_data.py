# backend/seed_data.py
from datetime import datetime, timezone
from backend.database import db
from backend.logger import setup_logger

logger = setup_logger(__name__)

def seed_database():
    """
    Populates the Firestore 'clinical_notes' collection with realistic mock data 
    to test the Reasoning RAG pipeline.
    """
    patient_id = "ID-11111" # John Smith
    
    # A realistic chronological timeline spanning a few years
    mock_notes = [
        {
            "patient_id": patient_id,
            "doctor_id": "DOC-111",
            "department": "General Practice",
            "date_recorded": datetime(2024, 2, 10, 9, 0, tzinfo=timezone.utc),
            "note_content": "Patient presents with moderate chest discomfort and shortness of breath after climbing stairs. Blood pressure is 145/90. EKG shows mild abnormalities. Referring to Cardiology for a full workup.",
            "tags": ["cardiovascular", "referral"]
        },
        {
            "patient_id": patient_id,
            "doctor_id": "DOC-205",
            "department": "Cardiology",
            "date_recorded": datetime(2024, 2, 28, 14, 30, tzinfo=timezone.utc),
            "note_content": "Performed echocardiogram. Results indicate mild left ventricular hypertrophy. Patient reports chest pain has subsided since resting. Prescribed 5mg Amlodipine daily for hypertension. Scheduled a 6-month follow-up.",
            "tags": ["hypertension", "medication", "echocardiogram"]
        },
        {
            "patient_id": patient_id,
            "doctor_id": "DOC-444",
            "department": "ER",
            "date_recorded": datetime(2025, 7, 4, 22, 15, tzinfo=timezone.utc),
            "note_content": "Patient admitted to ER with a deep laceration on the right forearm from a cooking accident. Cleaned wound and applied 6 sutures. No signs of nerve damage. Tetanus shot administered. Discharged with oral antibiotics (Amoxicillin 500mg) to prevent infection.",
            "tags": ["laceration", "sutures", "antibiotics"]
        },
        {
            "patient_id": patient_id,
            "doctor_id": "DOC-111",
            "department": "General Practice",
            "date_recorded": datetime(2026, 5, 15, 10, 0, tzinfo=timezone.utc),
            "note_content": "Annual checkup. Patient reports feeling well. Forearm wound has healed completely with minimal scarring. Patient has been taking Amlodipine regularly; blood pressure is well-controlled at 120/80. No new complaints.",
            "tags": ["annual review", "hypertension controlled"]
        }
    ]

    logger.info("Starting database seeding process...")
    
    collection_ref = db.collection("clinical_notes")
    
    success_count = 0
    for note in mock_notes:
        try:
            # We use .add() to let Firestore auto-generate the document IDs
            _, doc_ref = collection_ref.add(note)
            logger.info(f"Inserted note from {note['date_recorded'].strftime('%Y-%m-%d')} with ID: {doc_ref.id}")
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to insert note: {e}")
            
    logger.info(f"Database seeding complete. Successfully added {success_count} mock records.")

if __name__ == "__main__":
    seed_database()