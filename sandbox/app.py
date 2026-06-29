import streamlit as st
import pandas as pd
import json
import os
import sys
import streamlit.components.v1 as components

# Add parent dir to path to import src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client, Client

def sanitize_and_escape_text(raw_input_string: str) -> str:
    """
    Identifies raw dollar symbols inside standard alphanumeric text and 
    programmatically escapes them to prevent conflicts with Streamlit's LaTeX parser.
    """
    if not raw_input_string:
        return ""
    # Use a raw string regex pattern to escape literal dollar signs
    sanitized_text = raw_input_string.replace("$", r"\$")
    return sanitized_text

st.set_page_config(page_title="Redrob Sandbox", page_icon=":material/analytics:", layout="wide")

st.title("Redrob AI Candidate Ranking Sandbox (Direct-to-Cloud)")
st.write("This sandbox uses Supabase Direct-to-Cloud uploads to handle massive candidate files seamlessly.")

# --- Configuration ---
# In production, set these in Streamlit Cloud Secrets
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://YOUR_PROJECT.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR...")
BUCKET_NAME = "candidates"

st.sidebar.header("Supabase Configuration")
st.sidebar.write("Ensure your bucket is public or you handle auth.")
st.sidebar.code(f"URL: {SUPABASE_URL[:15]}...\nBucket: {BUCKET_NAME}")

# --- Custom Javascript Uploader ---
st.subheader("Upload candidates.jsonl")

custom_html = f"""
<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
  <style>
    body {{ font-family: sans-serif; color: white; }}
    .upload-btn {{ background: #ff4b4b; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }}
    .upload-btn:hover {{ background: #ff3333; }}
    .upload-btn:disabled {{ background: #666; cursor: not-allowed; }}
    
    .loader {{
      border: 4px solid #444;
      border-top: 4px solid #ff4b4b;
      border-radius: 50%;
      width: 20px;
      height: 20px;
      animation: spin 1s linear infinite;
      display: inline-block;
      vertical-align: middle;
      margin-right: 10px;
    }}
    
    @keyframes spin {{
      0% {{ transform: rotate(0deg); }}
      100% {{ transform: rotate(360deg); }}
    }}
    
    #status-container {{
      margin-top: 15px;
      padding: 10px;
      border-radius: 5px;
      display: none;
      align-items: center;
      background-color: rgba(0,0,0,0.2);
    }}
  </style>
</head>
<body>
  <p>Select your JSONL file to upload directly to Supabase:</p>
  <input type="file" id="fileInput" accept=".jsonl" />
  <button id="uploadBtn" class="upload-btn" onclick="uploadFile()">Direct Upload to Cloud</button>
  
  <div id="status-container">
    <div id="spinner" class="loader"></div>
    <span id="status" style="font-weight: bold;"></span>
  </div>

  <script>
    const supabase = supabase.createClient('{SUPABASE_URL}', '{SUPABASE_KEY}')
    
    async function uploadFile() {{
      const fileInput = document.getElementById('fileInput');
      const statusContainer = document.getElementById('status-container');
      const status = document.getElementById('status');
      const spinner = document.getElementById('spinner');
      const uploadBtn = document.getElementById('uploadBtn');
      
      if (!fileInput.files || fileInput.files.length === 0) {{
        statusContainer.style.display = 'flex';
        spinner.style.display = 'none';
        status.innerText = '⚠️ Please select a file first.';
        status.style.color = '#ffaa00';
        return;
      }}
      
      const file = fileInput.files[0];
      
      // Show loading state
      uploadBtn.disabled = true;
      statusContainer.style.display = 'flex';
      spinner.style.display = 'inline-block';
      status.innerText = 'Uploading ' + (file.size / (1024*1024)).toFixed(1) + ' MB... Please do not close this window.';
      status.style.color = 'white';
      
      const {{ data, error }} = await supabase.storage
        .from('{BUCKET_NAME}')
        .upload('uploads/candidates.jsonl', file, {{
          cacheControl: '3600',
          upsert: true
        }})
        
      // Handle response
      uploadBtn.disabled = false;
      spinner.style.display = 'none';
        
      if (error) {{
        status.innerText = '❌ Error: ' + error.message;
        status.style.color = '#ff4b4b';
      }} else {{
        status.innerText = '✅ Upload Complete! File safely stored in Supabase.';
        status.style.color = '#00cc66';
      }}
    }}
  </script>
</body>
</html>
"""

# Render the HTML component
components.html(custom_html, height=200)

st.markdown("<br><br>", unsafe_allow_html=True)

# Use a state variable to track if processing was clicked
if st.button("Simulate Backend Processing (Run Live ML Pipeline)"):
    st.info("Streaming file from Supabase and running live ML Inference (Zero-Memory Architecture)...")
    
    try:
        from src.models.semantic import SemanticMatcher
        from src.features.extractor import extract_features
        from src.ranker.explainer import generate_reasoning
        from src.features.honeypot import is_honeypot
        from src.data_loader import get_jd_text
        import requests
        import io
        
        JD_TEXT = get_jd_text()
        JD_REQUIRED_SKILLS = {"python", "elasticsearch", "faiss", "pinecone", "weaviate", "qdrant", 
                              "milvus", "opensearch", "machine learning", "nlp", "llm", 
                              "sentence-transformers", "bge", "e5", "ndcg", "mrr", "map", "a/b test"}
        
        # Connect to Supabase
        supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Generate a signed URL to stream the massive file without buffering it in the SDK
        signed_url_resp = supabase_client.storage.from_(BUCKET_NAME).create_signed_url("uploads/candidates.jsonl", 60)
        
        if "signedURL" not in signed_url_resp:
            st.error("Failed to generate signed URL. Make sure the file exists.")
            st.stop()
            
        file_url = signed_url_resp["signedURL"]
        
        valid_candidates = []
        total_scanned = 0
        
        st.write("Streaming and pre-filtering candidates (filtering out traps & unqualified)...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Stream the file line-by-line via HTTP
        with requests.get(file_url, stream=True) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    total_scanned += 1
                    cand = json.loads(line)
                    
                    if total_scanned % 1000 == 0:
                        # Streamlit UI updates can be slow, update every 1000
                        status_text.text(f"Scanned {total_scanned} candidates... Kept {len(valid_candidates)}")
                        # Fake a progress bar since we don't know total size natively over stream
                        progress_bar.progress(min(total_scanned / 100000.0, 1.0))
                    
                    if not is_honeypot(cand):
                        profile = cand.get("profile", {})
                        exp = profile.get("years_of_experience", 0)
                        
                        # Strict Memory Filter: Drop candidates with < 4 years experience
                        if exp >= 4:
                            skills = cand.get("skills", [])
                            cand_skills = {s.get("name", "").lower() for s in skills}
                            
                            text_blob = profile.get("summary", "").lower()
                            for job in cand.get("career_history", []):
                                text_blob += " " + job.get("title", "").lower() + " " + job.get("description", "").lower()
                                
                            has_python = "python" in cand_skills or "python" in text_blob
                            if has_python:
                                vector_techs = ["pinecone", "weaviate", "qdrant", "milvus", "opensearch", "elasticsearch", "faiss", "sentence-transformers", "bge", "e5", "openai embeddings"]
                                has_vector_tech = any(tech in cand_skills for tech in vector_techs) or any(tech in text_blob for tech in vector_techs)
                                
                                if has_vector_tech:
                                    valid_candidates.append(cand)
                                    
        progress_bar.progress(1.0)
        status_text.text(f"Stream complete! Scanned {total_scanned} total candidates. Valid for ML Inference: {len(valid_candidates)}")
        st.success(f"Successfully filtered pool down to {len(valid_candidates)} candidates using 0MB of persistent RAM.")
        
        if not valid_candidates:
            st.error("No valid candidates passed the strict JD pre-filter.")
        else:
            # Initialize models
            with st.spinner("Initializing SentenceTransformer & building FAISS index..."):
                matcher = SemanticMatcher()
                matcher.build_index(valid_candidates)
                
                # Search
                results = matcher.search(JD_TEXT, top_k=min(100, len(valid_candidates)))
                
                # Generate CSV string
                csv_output = "candidate_id,rank,score,reasoning\n"
                
                st.write("### :material/workspace_premium: Top Candidate Matches")
                
                for rank, (cand, sem_score) in enumerate(results, 1):
                    features = extract_features(cand, JD_REQUIRED_SKILLS)
                    reasoning = generate_reasoning(cand, features, sem_score)
                    
                    safe_reasoning = sanitize_and_escape_text(reasoning)
                    
                    final_score = (sem_score * 0.4) + (features['hard_skills_score'] * 0.3) + (features['exp_score'] * 0.15) + (features['behavioral_score'] * 0.15)
                    
                    csv_output += f"{cand['candidate_id']},{rank},{final_score:.4f},\"{reasoning}\"\n"
                    
                    # Only render top 10 on screen to avoid crashing browser
                    if rank <= 10:
                        with st.container():
                            st.markdown(f"#### #{rank} - {cand['candidate_id']}")
                            col1, col2 = st.columns([1, 4])
                            
                            with col1:
                                st.metric(label="Match Score", value=f"{int(final_score * 100)}%")
                                st.progress(min(max(final_score, 0.0), 1.0))
                                
                            with col2:
                                st.info(f"**Why they match:** {safe_reasoning}")
                                st.button("View Full Profile", key=f"btn_{cand['candidate_id']}", use_container_width=False)
                                
                            st.markdown("<br>", unsafe_allow_html=True)
                
                st.markdown("<br><br>", unsafe_allow_html=True)
                st.success(":material/check_circle: ML Pipeline finished successfully!")
                
                st.download_button(
                    label=":material/download: Download Full submission.csv",
                    data=csv_output,
                    file_name="submission.csv",
                    mime="text/csv"
                )
                        
    except Exception as e:
        st.error(f"Error during ML processing: {str(e)}")
        st.warning("If you see an 'Out of Memory' error or connection drop, the uploaded file was too large for Streamlit Community Cloud.")
