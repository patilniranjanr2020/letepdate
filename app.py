import streamlit as st
import pandas as pd

# Page Configuration
st.set_page_config(
    page_title="letepdate - Medical Cost & Risk Matrix",
    page_icon="🏥",
    layout="wide"
)

# App Title & Intro
st.title("🏥 letepdate: Medical Cost & Permanent Risk Matrix (India)")
st.markdown("""
Welcome to **letepdate**! This application breaks down the **safest techniques**, **all-inclusive expenses in India** (covering surgery, hospital stays, medication, and standard follow-ups), and whether wise medical measures can completely eliminate permanent organ/tissue failure risks.
""")

# Database Source
data = [
    {
        "Procedure": "Hair Transplant",
        "Safest Technique": "Surgeon-led FUE / Sapphire FUE",
        "Cost in India (INR)": "₹60,000 - ₹2,80,000",
        "Eliminate Permanent Organ Failure Risks?": "Yes",
        "Clinical Details": "External/surface tissue only. Proper technique avoids scarring/necrosis; zero systemic organ risk."
    },
    {
        "Procedure": "Limb Lengthening",
        "Safest Technique": "LON (Lengthening Over Nail) / PRECICE",
        "Cost in India (INR)": "₹6,50,000 - ₹18,00,000+",
        "Eliminate Permanent Organ Failure Risks?": "No",
        "Clinical Details": "Major orthopedic distraction. Wise measures reduce hazards, but nerve or bone complications cannot be reduced to absolute zero."
    },
    {
        "Procedure": "Myopia Correction",
        "Safest Technique": "Contoura Vision / LASIK / SMILE",
        "Cost in India (INR)": "₹45,000 - ₹1,30,000",
        "Eliminate Permanent Organ Failure Risks?": "Yes",
        "Clinical Details": "Superficial corneal reshaping. Pre-op screening fully filters out high-risk structural candidates."
    }
]

df = pd.DataFrame(data)

# Sidebar Options
st.sidebar.header("letepdate Controls")
selected_procedure = st.sidebar.multiselect(
    "Select Procedure(s) to Display:",
    options=df["Procedure"].tolist(),
    default=df["Procedure"].tolist()
)

# Filter Dataframe based on selection
filtered_df = df[df["Procedure"].isin(selected_procedure)]

# Display Table Section
st.subheader("📋 Comparison Dashboard")
st.dataframe(filtered_df, use_container_width=True)

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
st.caption("letepdate • Costs are general industry averages in India inclusive of standard hospital fees, surgical charges, and typical follow-ups. Always consult a certified board-qualified medical specialist.")