import json
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree

# Page Configuration
st.set_page_config(
    page_title="letepdate - Live Medical & Clinical Intelligence",
    page_icon="🏥",
    layout="wide"
)

# App Title & Intro
st.title("🏥 letepdate: Live Medical & Clinical Intelligence")
st.markdown("""
Welcome to **letepdate**! This application dynamically queries live open medical databases (**PubMed** & **ClinicalTrials.gov**) to display structured, real-time clinical studies, trial statuses, phases, and publications.
""")

st.warning(
    "Medical information is dynamically fetched from live public APIs for research only, not diagnosis or treatment. "
    "Always confirm suitability with a qualified specialist."
)

# Dynamic Search Terms
PROCEDURE_TOPICS = {
    "Hair Transplantation": "hair transplantation",
    "Limb Lengthening": "limb lengthening surgery",
    "Myopia Correction (LASIK/SMILE)": "myopia refractive surgery LASIK SMILE",
    "Organ & Tissue Transplantation": "organ transplantation tissue engineering",
    "Cardiovascular Interventions": "cardiovascular intervention cardiac surgery"
}


@st.cache_data(ttl=1800)
def fetch_clinical_trials_df(search_term, limit=10):
    """Fetch live clinical trials and return a clean structured Pandas DataFrame."""
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

        rows = []
        for study in data.get("studies", []):
            protocol = study.get("protocolSection", {})
            id_mod = protocol.get("identificationModule", {})
            status_mod = protocol.get("statusModule", {})
            design_mod = protocol.get("designModule", {})
            sponsor_mod = protocol.get("sponsorCollaboratorsModule", {})
            eligibility_mod = protocol.get("eligibilityModule", {})
            
            nct_id = id_mod.get("nctId", "N/A")
            title = id_mod.get("briefTitle", "Untitled")
            status = status_mod.get("overallStatus", "UNKNOWN")
            
            phases = design_mod.get("phases", ["N/A"])
            phase_str = ", ".join(phases) if isinstance(phases, list) else str(phases)
            
            sponsor = sponsor_mod.get("leadSponsor", {}).get("name", "Unlisted")
            min_age = eligibility_mod.get("minimumAge", "Not specified")
            sex = eligibility_mod.get("sex", "ALL")

            rows.append({
                "NCT ID": nct_id,
                "Trial Title": title,
                "Recruitment Status": status,
                "Phase": phase_str,
                "Lead Sponsor": sponsor,
                "Min Age": min_age,
                "Gender Eligibility": sex,
                "Link": f"https://clinicaltrials.gov/study/{nct_id}"
            })
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"Error fetching Clinical Trials: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=1800)
def fetch_pubmed_research_df(search_term, limit=10):
    """Fetch live PubMed articles and return a clean structured Pandas DataFrame."""
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
            return pd.DataFrame()

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

        rows = []
        for document in summary_root.findall(".//DocSum"):
            values = {
                item.attrib.get("Name"): item.text or ""
                for item in document.findall("Item")
            }
            pubmed_id = document.findtext("Id", "")
            rows.append({
                "PubMed ID": pubmed_id,
                "Article Title": values.get("Title", "Untitled"),
                "Publication Date": values.get("PubDate", "N/A"),
                "Journal": values.get("FullJournalName", "PubMed"),
                "Link": f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/"
            })
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"Error fetching PubMed research: {e}")
        return pd.DataFrame()


# Sidebar Controls
st.sidebar.header("🔍 Search Controls")
selected_procedure = st.sidebar.selectbox(
    "Select Medical Topic / Procedure:",
    options=list(PROCEDURE_TOPICS.keys())
)

custom_search = st.sidebar.text_input("Or enter custom query:", placeholder="e.g. cardiac stent, knee replacement")
result_limit = st.sidebar.slider("Number of records to fetch:", min_value=5, max_value=25, value=10)

if st.sidebar.button("🔄 Refresh Live Data"):
    st.cache_data.clear()
    st.rerun()

query_term = custom_search.strip() if custom_search.strip() else PROCEDURE_TOPICS[selected_procedure]

st.info(f"Showing live data for query: **'{query_term}'** (Refreshed at: `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}`)")

# Tabs for Structured Data Displays
tab1, tab2 = st.tabs(["🧪 Live Clinical Trials (ClinicalTrials.gov)", "📚 Latest Medical Research (PubMed)"])

with tab1:
    st.subheader("🧪 Live Clinical Trials Dataset")
    with st.spinner("Fetching active clinical trials..."):
        trials_df = fetch_clinical_trials_df(query_term, limit=result_limit)
        
    if not trials_df.empty:
        # Display summary metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Studies Fetched", len(trials_df))
        m2.metric("Recruiting Studies", len(trials_df[trials_df["Recruitment Status"].str.upper() == "RECRUITING"]))
        m3.metric("Phase 3/4 Trials", len(trials_df[trials_df["Phase"].str.contains("PHASE3|PHASE4", case=False, na=False)]))
        
        st.markdown("### 📋 Structured Trials Data")
        st.dataframe(
            trials_df,
            column_config={
                "Link": st.column_config.LinkColumn("Trial Link", display_text="View on ClinicalTrials.gov")
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("No active clinical trials found for this topic.")

with tab2:
    st.subheader("📚 Latest Published Research Papers")
    with st.spinner("Fetching PubMed research..."):
        pubmed_df = fetch_pubmed_research_df(query_term, limit=result_limit)
        
    if not pubmed_df.empty:
        st.markdown("### 📋 Structured Publications Data")
        st.dataframe(
            pubmed_df,
            column_config={
                "Link": st.column_config.LinkColumn("PubMed Link", display_text="Read Paper")
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("No recent PubMed articles found for this topic.")

# Footer & Disclaimer
st.markdown("---")
st.caption(
    "letepdate • All data dynamically fetched live from NCBI PubMed and US ClinicalTrials.gov REST APIs without hardcoded static storage. "
    "Always consult a certified board-qualified medical specialist."
)
