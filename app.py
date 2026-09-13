import json
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree

# Page Configuration
st.set_page_config(
    page_title="letepdate - AI Live Medical Matrix",
    page_icon="🏥",
    layout="wide"
)

# App Title & Intro
st.title("🏥 letepdate: AI-Powered Live Medical & Cost Intelligence (India)")
st.markdown("""
Welcome to **letepdate**! This application dynamically queries live open medical databases (**PubMed** & **ClinicalTrials.gov**) and uses **Google Gemini AI** to structure live medical research into a clear decision matrix (Safest Techniques, Cost in India in INR, Organ Failure Risk Elimination, and Age Limits).
""")

st.warning(
    "Medical information is dynamically generated via live APIs and AI for research only, not diagnosis or treatment. "
    "Always confirm suitability with a qualified medical specialist."
)

# API Configuration
GEMINI_API_KEY = "AQ.Ab8RN6IWXVUELHddAJ75zuCHMlf89UKrkfK26X_s1iz7-6_ljQ"

PROCEDURE_TOPICS = {
    "Hair Transplant": "hair transplantation surgical technique cost India safety age",
    "Limb Lengthening": "limb lengthening surgery distractors LON PRECICE cost India risk safety",
    "Myopia Correction (LASIK / SMILE)": "myopia refractive surgery LASIK SMILE Contoura cost India safety age",
    "Organ & Tissue Transplant": "organ tissue transplantation organ failure risk cost India age limit",
    "Cardiovascular Surgery": "cardiac surgery bypass angioplasty risk cost India age limit"
}


@st.cache_data(ttl=1800)
def fetch_clinical_trials_raw(search_term, limit=5):
    """Fetch live clinical trials raw text summaries from ClinicalTrials.gov API v2."""
    try:
        query = urlencode({
            "query.cond": search_term,
            "pageSize": limit,
            "format": "json"
        })
        request = Request(
            f"https://clinicaltrials.gov/api/v2/studies?{query}",
            headers={"User-Agent": "letepdate/1.0"}
        )
        with urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        summaries = []
        for study in data.get("studies", []):
            protocol = study.get("protocolSection", {})
            id_mod = protocol.get("identificationModule", {})
            title = id_mod.get("briefTitle", "Untitled")
            status = protocol.get("statusModule", {}).get("overallStatus", "UNKNOWN")
            summary = protocol.get("descriptionModule", {}).get("briefSummary", "")
            summaries.append(f"Trial Title: {title} | Status: {status} | Summary: {summary[:200]}")
        return "\n".join(summaries)
    except Exception:
        return "No clinical trials data retrieved."


@st.cache_data(ttl=1800)
def fetch_pubmed_raw(search_term, limit=5):
    """Fetch live PubMed publication titles and sources."""
    try:
        query = urlencode({
            "db": "pubmed",
            "term": search_term,
            "retmax": limit,
            "sort": "date",
            "retmode": "xml"
        })
        request = Request(
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{query}",
            headers={"User-Agent": "letepdate/1.0"}
        )
        with urlopen(request, timeout=10) as response:
            search_root = ElementTree.fromstring(response.read())

        article_ids = [node.text for node in search_root.findall(".//Id") if node.text]
        if not article_ids:
            return "No PubMed articles retrieved."

        summary_query = urlencode({
            "db": "pubmed",
            "id": ",".join(article_ids),
            "retmode": "xml"
        })
        summary_request = Request(
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?{summary_query}",
            headers={"User-Agent": "letepdate/1.0"}
        )
        with urlopen(summary_request, timeout=10) as response:
            summary_root = ElementTree.fromstring(response.read())

        articles = []
        for document in summary_root.findall(".//DocSum"):
            values = {
                item.attrib.get("Name"): item.text or ""
                for item in document.findall("Item")
            }
            articles.append(f"Title: {values.get('Title')} | Journal: {values.get('FullJournalName')}")
        return "\n".join(articles)
    except Exception:
        return "No PubMed articles retrieved."


@st.cache_data(ttl=3600)
def analyze_with_gemini(procedure_name, search_term):
    """Call Google Gemini API to structure live medical research into a clear JSON table schema."""
    trials_text = fetch_clinical_trials_raw(search_term)
    pubmed_text = fetch_pubmed_raw(search_term)
    
    prompt = f"""
    Analyze the following live clinical and medical research data for the medical procedure: "{procedure_name}".
    
    Live Clinical Trials Data:
    {trials_text}
    
    Live PubMed Research:
    {pubmed_text}
    
    Provide an accurate, structured JSON object representing the procedure in India. Do NOT include markdown codeblocks or extra text. Output ONLY valid JSON in this exact structure:
    {{
        "Procedure": "{procedure_name}",
        "Safest & Best Technique": "Name of safest technique",
        "Cost in India (INR)": "Estimated range in ₹ INR",
        "Can Permanent Organ/Tissue Failure Risk be Zero?": "Yes or No ONLY",
        "Recommended Age Limits": "e.g. 18 - 60 years",
        "Clinical Rationale": "Brief 1-2 sentence medical rationale explaining why risk CAN or CANNOT be reduced to absolute zero even with the safest state-of-the-art technique."
    }}
    
    STRICT RULE FOR 'Can Permanent Organ/Tissue Failure Risk be Zero?':
    - Output ONLY 'Yes' or 'No'. Do NOT use 'Partial', 'Depends', or 'Maybe'.
    - If it is IMPOSSIBLE to guarantee zero permanent damage or organ/tissue failure risk (even using the safest, highest state-of-the-art technology available), you MUST answer 'No'.
    - Only answer 'Yes' if the procedure is purely superficial/external or pre-screened such that permanent systemic organ/tissue failure risk is genuinely zero.
    """
    
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY
    }
    
    payload = json.dumps({
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }).encode('utf-8')
    
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
        req = Request(url, data=payload, headers=headers, method="POST")
        with urlopen(req, timeout=15) as response:
            res_body = json.loads(response.read().decode('utf-8'))
            
        candidate_text = res_body['candidates'][0]['content']['parts'][0]['text'].strip()
        # Clean potential markdown formatting
        if candidate_text.startswith("```json"):
            candidate_text = candidate_text[7:]
        if candidate_text.startswith("```"):
            candidate_text = candidate_text[3:]
        if candidate_text.endswith("```"):
            candidate_text = candidate_text[:-3]
            
        return json.loads(candidate_text.strip())
    except Exception as e:
        return {
            "Procedure": procedure_name,
            "Safest & Best Technique": "Surgeon-led Assessment",
            "Cost in India (INR)": "₹50,000 - ₹5,00,000+",
            "Eliminate Permanent Organ Failure Risk?": "Depends on procedure scope",
            "Recommended Age Limits": "18+ years",
            "Clinical Rationale": f"AI Processing note: {str(e)}"
        }


# Sidebar Controls
st.sidebar.header("🔍 Dynamic Selection")
selected_procedures = st.sidebar.multiselect(
    "Select Procedure(s) for AI Live Matrix:",
    options=list(PROCEDURE_TOPICS.keys()),
    default=["Hair Transplant", "Limb Lengthening", "Myopia Correction (LASIK / SMILE)"]
)

if st.sidebar.button("🔄 Force Refresh AI & Live Data"):
    st.cache_data.clear()
    st.rerun()

st.subheader("📋 AI-Generated Live Decision Matrix")
st.caption(
    "Live medical research from PubMed & ClinicalTrials.gov structured dynamically using Google Gemini AI. "
    f"Last refreshed: `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}`"
)

if selected_procedures:
    matrix_data = []
    with st.spinner("Fetching live APIs and processing with Gemini AI..."):
        for proc in selected_procedures:
            item = analyze_with_gemini(proc, PROCEDURE_TOPICS[proc])
            matrix_data.append(item)
            
    matrix_df = pd.DataFrame(matrix_data)
    
    # Display Primary Decision Matrix Table
    st.dataframe(
        matrix_df.drop(columns=["Clinical Rationale"]),
        use_container_width=True,
        hide_index=True
    )
    
    # Detailed Insights Accordion
    st.subheader("🔍 Deep-Dive AI Clinical Insights")
    for row in matrix_data:
        with st.expander(f"🔬 {row.get('Procedure', '')} — {row.get('Safest & Best Technique', '')}"):
            c1, c2, c3 = st.columns(3)
            c1.metric("Est. Cost in India (INR)", row.get("Cost in India (INR)", "N/A"))
            c2.metric("Can Permanent Risk be Zero?", row.get("Can Permanent Organ/Tissue Failure Risk be Zero?", "No"))
            c3.metric("Age Limits", row.get("Recommended Age Limits", "N/A"))
            st.markdown(f"**AI Safety Rationale:** {row.get('Clinical Rationale', 'N/A')}")

else:
    st.info("Please select at least one procedure from the sidebar.")

# Footer & Disclaimer
st.markdown("---")
st.caption(
    "letepdate • Powered by live PubMed, ClinicalTrials.gov APIs and Google Gemini AI. "
    "Always consult a certified board-qualified medical specialist."
)
