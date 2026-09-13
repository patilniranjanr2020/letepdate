import json
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree

# Page Configuration
st.set_page_config(
    page_title="letepdate - Medical Cost & Risk Matrix",
    page_icon="🏥",
    layout="wide"
)

# App Title & Intro
st.title("🏥 letepdate: Medical Cost & Permanent Risk Matrix (India)")
st.markdown("""
Welcome to **letepdate**! This application breaks down **safest techniques**, **expenses in India**, **live clinical trial data**, and **latest research** to assess whether medical measures can eliminate permanent organ/tissue failure risks.
""")

st.warning(
    "Medical information is for research only, not diagnosis or treatment. "
    "Always confirm suitability with a qualified specialist."
)

# Database Source
data = [
    {
        "Procedure": "Hair Transplant",
        "Safest Technique": "Surgeon-led FUE / Sapphire FUE",
        "Cost in India (INR)": "₹60,000 - ₹2,80,000",
        "Eliminate Permanent Organ Failure Risks?": "Yes",
        "Male Lower Age": 18,
        "Male Upper Age": 65,
        "Search Query": "hair transplantation",
        "Clinical Details": "External/surface tissue only. Proper technique avoids scarring/necrosis; zero systemic organ risk."
    },
    {
        "Procedure": "Limb Lengthening",
        "Safest Technique": "LON (Lengthening Over Nail) / PRECICE",
        "Cost in India (INR)": "₹6,50,000 - ₹18,00,000+",
        "Eliminate Permanent Organ Failure Risks?": "No",
        "Male Lower Age": 18,
        "Male Upper Age": 45,
        "Search Query": "limb lengthening surgery",
        "Clinical Details": "Major orthopedic distraction. Wise measures reduce hazards, but nerve or bone complications cannot be reduced to absolute zero."
    },
    {
        "Procedure": "Myopia Correction",
        "Safest Technique": "Contoura Vision / LASIK / SMILE",
        "Cost in India (INR)": "₹45,000 - ₹1,30,000",
        "Eliminate Permanent Organ Failure Risks?": "Yes",
        "Male Lower Age": 18,
        "Male Upper Age": 45,
        "Search Query": "myopia refractive surgery LASIK SMILE",
        "Clinical Details": "Superficial corneal reshaping. Pre-op screening fully filters out high-risk structural candidates."
    }
]

df = pd.DataFrame(data)


@st.cache_data(ttl=3600)
def fetch_latest_research(search_term, limit=5):
    """Fetch recent research records automatically from the free PubMed E-utilities API (No API key required)."""
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
            return []

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
            pubmed_id = document.findtext("Id", "")
            articles.append({
                "Title": values.get("Title", "Untitled"),
                "Published": values.get("PubDate", "Date unavailable"),
                "Source": values.get("FullJournalName", "PubMed"),
                "Link": f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/"
            })
        return articles
    except Exception as e:
        st.error(f"Error connecting to PubMed API: {e}")
        return []


@st.cache_data(ttl=3600)
def fetch_clinical_trials(search_term, limit=5):
    """Fetch live recruiting/active clinical trials automatically from the free ClinicalTrials.gov API v2 (No API key required)."""
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

        studies = []
        for study in data.get("studies", []):
            protocol = study.get("protocolSection", {})
            id_module = protocol.get("identificationModule", {})
            status_module = protocol.get("statusModule", {})
            design_module = protocol.get("designModule", {})
            
            nct_id = id_module.get("nctId", "")
            title = id_module.get("briefTitle", "Untitled Trial")
            status = status_module.get("overallStatus", "UNKNOWN")
            phases = design_module.get("phases", ["N/A"])
            phase_str = ", ".join(phases) if isinstance(phases, list) else str(phases)

            studies.append({
                "NCTId": nct_id,
                "Title": title,
                "Status": status,
                "Phase": phase_str,
                "Link": f"https://clinicaltrials.gov/study/{nct_id}"
            })
        return studies
    except Exception as e:
        st.error(f"Error connecting to ClinicalTrials.gov API: {e}")
        return []


# Sidebar Options
st.sidebar.header("letepdate Controls")
selected_procedure = st.sidebar.multiselect(
    "Select Procedure(s) to Display:",
    options=df["Procedure"].tolist(),
    default=df["Procedure"].tolist()
)
st.sidebar.subheader("Male Age Range")
male_lower_age = st.sidebar.number_input(
    "Lower age",
    min_value=18,
    max_value=100,
    value=18,
    step=1
)
male_upper_age = st.sidebar.number_input(
    "Upper age",
    min_value=18,
    max_value=100,
    value=65,
    step=1
)

if st.sidebar.button("🔄 Force Refresh Live Data"):
    st.cache_data.clear()
    st.rerun()

if male_lower_age > male_upper_age:
    st.sidebar.error("Lower age must be less than or equal to upper age.")
    filtered_df = df.iloc[0:0]
else:
    filtered_df = df[
        df["Male Lower Age"].le(male_upper_age)
        & df["Male Upper Age"].ge(male_lower_age)
    ]

# Filter Dataframe based on selection
filtered_df = filtered_df[filtered_df["Procedure"].isin(selected_procedure)]

st.info(
    f"Showing procedures for men aged {male_lower_age}-{male_upper_age}. "
    "Age ranges are general guidance and require specialist assessment."
)

# Display Table Section
st.subheader("📋 Comparison Dashboard")
st.dataframe(filtered_df.drop(columns=["Search Query"]), use_container_width=True)

# Live Data Feed Section: Research & Clinical Trials
st.subheader("🌐 Live Data Feeds (PubMed & ClinicalTrials.gov APIs)")
st.caption(
    "Data automatically fetched live from NCBI PubMed & US ClinicalTrials.gov open APIs. "
    f"Last refreshed: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
)

for _, row in filtered_df.iterrows():
    st.markdown(f"### 🔬 {row['Procedure']}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander(f"📚 Latest PubMed Research ({row['Procedure']})", expanded=True):
            latest_articles = fetch_latest_research(row["Search Query"])
            if not latest_articles:
                st.info("No recent PubMed records found.")
            for article in latest_articles:
                st.markdown(
                    f"- **[{article['Title']}]({article['Link']})**  \n"
                    f"  *{article['Published']} • {article['Source']}*"
                )
                
    with col2:
        with st.expander(f"🧪 Active Clinical Trials ({row['Procedure']})", expanded=True):
            trials = fetch_clinical_trials(row["Search Query"])
            if not trials:
                st.info("No active clinical trials found.")
            for trial in trials:
                st.markdown(
                    f"- **[{trial['Title']}]({trial['Link']})**  \n"
                    f"  `Status: {trial['Status']}` | `Phase: {trial['Phase']}` | ID: `{trial['NCTId']}`"
                )

# Detailed Accordion Section
st.subheader("🔍 Deep-Dive Insights & Safety Breakdown")
for index, row in filtered_df.iterrows():
    with st.expander(f"{row['Procedure']} — ({row['Safest Technique']})"):
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Estimated Cost (INR)", value=row['Cost in India (INR)'])
        with col2:
            st.metric(label="Can Permanent Risks be Eliminated?", value=row['Eliminate Permanent Organ Failure Risks?'])
        st.write(f"**Clinical Context:** {row['Clinical Details']}")

# Footer & Disclaimer
st.markdown("---")
st.caption(
    "letepdate • Costs are general estimates, not live quotes. Live research & trials sourced automatically from PubMed and ClinicalTrials.gov. "
    "Always consult a certified board-qualified medical specialist."
)