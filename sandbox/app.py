import streamlit as st
import pandas as pd
import json
import os
import streamlit.components.v1 as components

st.set_page_config(page_title="Redrob Sandbox", layout="wide")

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
  </style>
</head>
<body>
  <p>Select your 350MB JSONL file to upload directly to Supabase:</p>
  <input type="file" id="fileInput" accept=".jsonl" />
  <button class="upload-btn" onclick="uploadFile()">Direct Upload to Cloud</button>
  <p id="status"></p>

  <script>
    const supabase = supabase.createClient('{SUPABASE_URL}', '{SUPABASE_KEY}')
    
    async function uploadFile() {{
      const fileInput = document.getElementById('fileInput');
      const status = document.getElementById('status');
      
      if (!fileInput.files || fileInput.files.length === 0) {{
        status.innerText = 'Please select a file first.';
        return;
      }}
      
      const file = fileInput.files[0];
      status.innerText = 'Uploading directly to Supabase... please wait.';
      
      const {{ data, error }} = await supabase.storage
        .from('{BUCKET_NAME}')
        .upload('uploads/' + file.name, file, {{
          cacheControl: '3600',
          upsert: true
        }})
        
      if (error) {{
        status.innerText = 'Error: ' + error.message;
        status.style.color = '#ff4b4b';
      }} else {{
        status.innerText = 'Upload Complete! ✅ File safely stored in Supabase.';
        status.style.color = '#00cc66';
      }}
    }}
  </script>
</body>
</html>
"""

# Render the HTML component
components.html(custom_html, height=200)

st.write("---")
if st.button("Simulate Backend Processing"):
    st.info("In a real environment, the Streamlit python backend would now use the `supabase-py` SDK to stream the file from the bucket and run the FAISS ranking pipeline.")
    
    st.write("### 🏆 Top Candidate Matches")
    
    # Mock data for demonstration
    mock_results = [
        {"id": "CAND_0002025", "rank": 1, "score": 0.95, "reasoning": "Strong semantic match to JD requirements and ideal 5.9 years of experience."},
        {"id": "CAND_0046064", "rank": 2, "score": 0.90, "reasoning": "High overlap with required tech stack and strong GitHub activity."},
        {"id": "CAND_0081846", "rank": 3, "score": 0.88, "reasoning": "Ideal location match and highly active profile."}
    ]
    
    for candidate in mock_results:
        with st.container():
            st.markdown(f"#### #{candidate['rank']} - {candidate['id']}")
            col1, col2 = st.columns([1, 4])
            
            with col1:
                st.metric(label="Match Score", value=f"{int(candidate['score'] * 100)}%")
                st.progress(candidate['score'])
                
            with col2:
                st.info(f"**Why they match:** {candidate['reasoning']}")
                st.button("View Full Profile", key=candidate['id'], use_container_width=False)
                
            st.divider()
