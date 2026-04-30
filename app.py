import streamlit as st
import tempfile
import os
from campaign_agent import read_brief_from_doc, run_campaign_agent

st.set_page_config(page_title="Windstar Campaign Agent", page_icon="🚢", layout="wide")

st.title("Windstar Cruises Campaign Launch Agent")
st.markdown("Upload a campaign brief Word document and the AI will generate a complete campaign package.")

uploaded_file = st.file_uploader("Upload your campaign brief (.docx)", type=["docx"])

if uploaded_file:
    st.success("Brief uploaded successfully!")

    if st.button("Generate Campaign Package", type="primary"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        with st.spinner("AI agents are working on your campaign..."):
            try:
                brief = read_brief_from_doc(tmp_path)
                result = run_campaign_agent(brief)

                st.success("Campaign package complete!")

                st.divider()

                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Email Copy")
                    st.markdown(f"**Subject Line**")
                    st.info(result["subject"])
                    st.markdown(f"**Email Body**")
                    st.write(result["body"])

                with col2:
                    st.subheader("Strategy")
                    st.markdown(f"**Target Audience**")
                    st.write(result["audience"])
                    st.markdown(f"**Key Message**")
                    st.write(result["message"])

                st.divider()

                st.subheader("Channel Angles")
                col3, col4 = st.columns(2)

                with col3:
                    st.markdown("**Paid Social**")
                    st.write(result["social_angle"])
                    st.markdown("**Direct Mail**")
                    st.write(result["mail_angle"])

                with col4:
                    st.markdown("**SMS**")
                    st.write(result["sms_angle"])
                    st.markdown("**Email Angle**")
                    st.write(result["email_angle"])

                st.divider()

                st.subheader("Research Context")
                col5, col6 = st.columns(2)

                with col5:
                    st.markdown("**Actual Conditions**")
                    st.write(result["conditions"])
                    st.markdown("**Experiential Highlights**")
                    st.write(result["highlights"])

                with col6:
                    st.markdown("**Travel Advisories**")
                    st.write(result["advisories"])
                    st.markdown("**Traveler Sentiment**")
                    st.write(result["sentiment"])

                st.divider()

                st.subheader("Critic Review")
                score_col, rest_col = st.columns([1, 3])

                with score_col:
                    st.metric("Score", result["score"])

                with rest_col:
                    st.markdown("**Strengths**")
                    st.write(result["strengths"])
                    st.markdown("**Improvements**")
                    st.write(result["improvements"])

            except Exception as e:
                st.error(f"Something went wrong: {str(e)}")

            finally:
                os.unlink(tmp_path)
