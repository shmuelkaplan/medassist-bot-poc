import streamlit as st
import requests


API_URL = 'https://medassist-backend-oquu.onrender.com'

# Configure the page layout to use the full width for the chat interface
st.set_page_config(page_title="MedAssist Portal", page_icon="🩺", layout="wide")

# --- STATE MANAGEMENT ---
# Initialize our short-term memory variables if they don't exist yet
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_patient" not in st.session_state:
    st.session_state.current_patient = None

# --- UI RENDER FUNCTIONS ---

def render_login_screen():
    """Renders the secure provider authentication view."""
    # Using columns to center the login box to match the Figma design
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h2 style='text-align: center; color: #1E3A8A;'>MedAssist Portal</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Secure Provider Authentication</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            provider_id = st.text_input("Provider ID", placeholder="e.g. DOC-12345")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Sign In →", use_container_width=True)
            
            if submitted:
                # Mock authentication for now
                if provider_id and password:
                    st.session_state.logged_in = True
                    st.session_state.provider_id = provider_id
                    st.rerun() # Force Streamlit to reload and check the state

def render_search_screen():
    """Renders the patient search and recently viewed screen."""
    # Top Right Sign Out Button
    col1, col2 = st.columns([8, 1])
    with col2:
        if st.button("Sign Out"):
            st.session_state.logged_in = False
            st.rerun()

    st.markdown(f"<h1 style='text-align: center;'>Welcome, {st.session_state.provider_id}</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Enter a patient ID or MRN to access their records.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("search_form"):
            patient_id = st.text_input("Patient Identifier", placeholder="e.g. p1 or MRN-12345")
            submitted = st.form_submit_button("Access File →")
            
            if submitted and patient_id:
                st.session_state.current_patient = patient_id
                st.rerun()


def return_to_search():
    """Callback to instantly clear patient state before the UI renders."""
    st.session_state.current_patient = None
    st.session_state.timeline_data = None

def render_patient_dashboard():
    """Renders the main clinical dashboard dynamically using Backend API data."""
    
    # --- 1. DATA FETCHING & CACHING ---
    # Check if we need to fetch the data (either it's missing, or we switched patients)
# Check if we need to fetch the data
    if st.session_state.get("timeline_data") is None or st.session_state.get("last_fetched_patient") != st.session_state.current_patient:
        with st.spinner("Fetching patient records and generating AI summary..."):
            try:
                # Call our new BFF endpoint
                url = f"{API_URL}/patients/{st.session_state.current_patient}/timeline"
                response = requests.get(url)
                
                if response.status_code == 200:
                    st.session_state.timeline_data = response.json()
                    st.session_state.last_fetched_patient = st.session_state.current_patient
                elif response.status_code == 404:
                    st.warning("No clinical notes found for this patient.")
                    st.session_state.timeline_data = None
                else:
                    st.error(f"Logic Tier Error: {response.text}")
                    st.session_state.timeline_data = None
            except requests.exceptions.ConnectionError:
                st.error("CRITICAL ERROR: Could not connect to Logic Tier.")
                st.session_state.timeline_data = None

    # Retrieve the cached data
    timeline = st.session_state.get("timeline_data")
    
    # --- 2. SIDEBAR RENDERING ---
    with st.sidebar:
        if st.button("← Back to Search", on_click=return_to_search):
            st.session_state.current_patient = None
            # Clear the cache so it fetches fresh next time
            st.session_state.timeline_data = None 
            st.rerun()
            
        st.divider()
        st.subheader(f"👤 Patient: {st.session_state.current_patient}")
        st.caption("ID Verified")
        

    # --- 3. MAIN AREA: TABS ---
    tab_chat, tab_notes, tab_records, tab_analytics = st.tabs(["💬 AI Assistant", "📝 Add Clinical Note", "🗂️ Patient Records", "📊 Patient Analytics"])
    
    # --- TAB 1: AI Chat ---
    with tab_chat:
        st.subheader("Interactive Patient File")
        with st.chat_message("assistant"):
            st.write(f"Hello Dr. {st.session_state.provider_id}! I'm loaded with {st.session_state.current_patient}'s chart. How can I assist you today?")
            
        prompt = st.chat_input("Ask about this patient's records...")
        if prompt:
            with st.chat_message("user"):
                st.write(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Analyzing patient history and reasoning..."):
                    payload = {"patient_id": st.session_state.current_patient, "question": prompt}
                    try:
                        response = requests.post(f"{API_URL}/query/", json=payload)
                        if response.status_code == 200:
                            st.write(response.json().get("answer"))
                        else:
                            st.error("Logic Tier Error.")
                    except requests.exceptions.ConnectionError:
                        st.error("Cannot connect to backend.")

    # --- TAB 2: Add New Note (WITH REFRESH FIX) ---
    with tab_notes:
        st.subheader("File New Clinical Note")
        with st.form("new_note_form"):
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("Patient MRN", value=st.session_state.current_patient, disabled=True)
            with col2:
                department = st.selectbox("Department", ["General Practice", "Cardiology", "Radiology", "Neurology", "ER"])
            
            note_content = st.text_area("Clinical Observations", height=200)
            submitted = st.form_submit_button("Save to Patient File")
            
            if submitted and len(note_content) >= 10:
                payload = {
                    "patient_id": st.session_state.current_patient,
                    "doctor_id": st.session_state.provider_id,
                    "department": department,
                    "note_content": note_content,
                    "tags": []
                }
                try:
                    res = requests.post(f"{API_URL}/notes/", json=payload)
                    if res.status_code == 200:
                        st.success("Note saved!")
                        st.session_state.timeline_data = None # Drop Cache
                        st.rerun() # <--- THE REFRESH FIX: Forces UI to reboot instantly
                    else:
                        st.error("Failed to save.")
                except Exception:
                    st.error("Backend offline.")

    # --- TAB 3: View/Edit Records (RBAC AUTHORIZATION) ---
    with tab_records:
        st.subheader("Complete Medical History")
        
        if timeline:
            # Combine both lists to show all notes in one place
            all_visits = timeline.get("recent_visits", []) + timeline.get("older_visits", [])
            
            for visit in all_visits:
                doc_id = visit.get("document_id")
                author_id = visit.get("doctor_id")
                date_str = visit.get("date_recorded")[:10]
                
                # Use an expander for each file to keep the UI clean
                with st.expander(f"{date_str} | {visit.get('department')} | Attending: {author_id}"):
                    
                    # Authorization Logic: Can this doctor edit this note?
                    if author_id == st.session_state.provider_id:
                        # EDIT MODE
                        st.caption("✏️ You are the author. You may update this record.")
                        with st.form(key=f"edit_form_{doc_id}"):
                            updated_text = st.text_area("Edit Clinical Note", value=visit.get("note_content"), height=150)
                            if st.form_submit_button("Update Note"):
                                try:
                                    # Send the PUT request to our new endpoint
                                    update_res = requests.put(
                                        f"{API_URL}/notes/{doc_id}", 
                                        json={"note_content": updated_text}
                                    )
                                    if update_res.status_code == 200:
                                        st.success("Record updated.")
                                        st.session_state.timeline_data = None # Drop Cache
                                        st.rerun() # Refresh the UI immediately
                                    else:
                                        st.error("Update failed.")
                                except Exception:
                                    st.error("Backend offline.")
                    else:
                        # VIEW ONLY MODE
                        st.caption("🔒 View Only. You are not the author of this record.")
                        st.info(visit.get("note_content"))
    
    # --- TAB 4: THE NEW ANALYTICS DASHBOARD (DYNAMIC) ---
    with tab_analytics:
        st.subheader("📊 AI-Extracted Patient Analytics")
        st.caption("These statistics are automatically generated by the AI Extractor Pipeline from unstructured clinical notes.")
        
        if timeline and "snapshot" in timeline:
            snapshot = timeline.get("snapshot", {})
            
            # 1. Primary Clinical Status Block
            st.subheader("🩺 Dynamic Clinical Snapshot")
            status = snapshot.get("current_clinical_picture", "No clinical picture provided.")
            st.info(f"**Summery:** {status}")
            
            # 2. Main Medical Grid (2 Columns)
            col_left, col_right = st.columns(2)
            
            with col_left:
                st.markdown("### 🧬 Active Diagnoses")
                diagnoses = snapshot.get("active_diagnoses", [])
                if diagnoses:
                    for d in diagnoses:
                        st.markdown(f"- {d}")
                else:
                    st.caption("No active diagnoses detected.")
                    
                st.markdown("### ⏳ Pending Tests & Treatments")
                pending = snapshot.get("pending_tests_and_treatments", [])
                if pending:
                    for p in pending:
                        st.markdown(f"• {p}")
                else:
                    st.caption("No pending items found.")

            with col_right:
                st.markdown("### 💊 Regular Medications")
                meds = snapshot.get("regular_medications", [])
                if meds:
                    for m in meds:
                        st.markdown(f"- {m}")
                else:
                    st.caption("No regular medications listed.")
                    
                st.markdown("### 📅 Scheduled Future Procedures")
                future = snapshot.get("future_procedures", [])
                if future:
                    for f in future:
                        st.markdown(f"• {f}")
                else:
                    st.caption("No upcoming procedures scheduled.")
            
# 3. DYNAMIC CATCH-ALL: Render any extra keys the AI invented!
            core_keys = ["current_clinical_picture", "active_diagnoses", "regular_medications", "pending_tests_and_treatments", "future_procedures"]
            extra_clinical_data = {k: v for k, v in snapshot.items() if k not in core_keys}
            
            if extra_clinical_data:
                st.divider()
                st.markdown("### 📌 Additional Clinical Context")
                extra_cols = st.columns(2)
                
                for i, (category, data_list) in enumerate(extra_clinical_data.items()):
                    with extra_cols[i % 2]:
                        display_title = category.replace("_", " ").title()
                        st.markdown(f"**{display_title}**")
                        
                        # --- THE NEW NESTED DICTIONARY HANDLER ---
                        if isinstance(data_list, dict):
                            # The AI nested another dictionary! Unpack it beautifully.
                            for sub_key, sub_val in data_list.items():
                                clean_sub_key = sub_key.replace("_", " ").title()
                                
                                # If the sub-value is a list (like allergies: ['Peanuts'])
                                if isinstance(sub_val, list):
                                    # Join the list into a comma-separated string
                                    joined_list = ", ".join(str(item) for item in sub_val)
                                    st.markdown(f"- **{clean_sub_key}:** {joined_list}")
                                else:
                                    # It's just a normal string
                                    st.markdown(f"- **{clean_sub_key}:** {sub_val}")
                                    
                        # --- EXISTING HANDLERS FOR LISTS AND STRINGS ---
                        elif isinstance(data_list, list):
                            for item in data_list:
                                st.markdown(f"- {item}")
                        else:
                            st.markdown(f"- {data_list}")
            
            st.divider()



# --- MAIN ROUTER ---
# This acts as the traffic cop, deciding which function to run based on state
if not st.session_state.logged_in:
    render_login_screen()
elif st.session_state.current_patient is None:
    render_search_screen()
else:
    render_patient_dashboard()