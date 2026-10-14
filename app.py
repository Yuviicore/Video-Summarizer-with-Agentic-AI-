
import os
import time
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load local environment variables if available
load_dotenv()

# Streamlit page configuration
st.set_page_config(
    page_title="TalkToVideo - AI Video Summarizer",
    page_icon="🎥",
    layout="wide"
)

st.title("TalkToVideo 🎥🧠💬")
st.header("AI Video Summarizer powered by Gemini")

# Load API key from Streamlit Secrets or local .env
try:
    API_KEY = st.secrets.get("GOOGLE_API_KEY", "")
except Exception:
    API_KEY = ""

if not API_KEY:
    API_KEY = os.getenv("GOOGLE_API_KEY", "")

if not API_KEY:
    st.error(
        "Google API key is missing. "
        "Add GOOGLE_API_KEY in Streamlit Settings > Secrets."
    )
    st.stop()

# Initialize the Google GenAI client
client = genai.Client(api_key=API_KEY)

# Upload a video
video_file = st.file_uploader(
    label="Upload your video",
    type=["mp4", "mov", "avi"],
    help="Upload a video to analyze. Keep it below 200 MB."
)

if video_file is not None:
    file_size_mb = len(video_file.getvalue()) / (1024 * 1024)

    if file_size_mb > 200:
        st.error("Please upload a video smaller than 200 MB.")
        st.stop()

    st.video(video_file)

    user_query = st.text_area(
        "What insights are you seeking from the video?",
        placeholder=(
            "Example: Summarize this video and explain "
            "the main points."
        ),
        help="Ask a specific question about the video."
    )

    if st.button("🔍 Analyze Video", type="primary"):
        if not user_query.strip():
            st.warning("Please enter a question about the video.")
        else:
            video_path = None
            uploaded_video = None

            try:
                # Save the uploaded video temporarily
                suffix = Path(video_file.name).suffix or ".mp4"

                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=suffix
                ) as temp_video:
                    temp_video.write(video_file.getvalue())
                    video_path = temp_video.name

                with st.spinner(
                    "Uploading and processing your video..."
                ):
                    # Upload using the Google GenAI SDK
                    uploaded_video = client.files.upload(
                        file=video_path
                    )

                    # Wait for video processing to finish
                    while (
                        uploaded_video.state is not None
                        and uploaded_video.state.name == "PROCESSING"
                    ):
                        time.sleep(2)
                        uploaded_video = client.files.get(
                            name=uploaded_video.name
                        )

                    if (
                        uploaded_video.state is not None
                        and uploaded_video.state.name == "FAILED"
                    ):
                        raise RuntimeError(
                            "Google could not process this video. "
                            "Try another MP4 video."
                        )

                # Build the video input for Gemini
                video_part = types.Part.from_uri(
                    file_uri=uploaded_video.uri,
                    mime_type=uploaded_video.mime_type
                )

                analysis_prompt = f"""
You are an AI video analysis assistant.

Analyze the uploaded video carefully and answer the user's question.

User question:
{user_query}

Provide a clear, accurate, well-organized response.
Summarize the main events, important details, and key takeaways
that are relevant to the user's question.
Do not invent details that are not supported by the video.
"""

                with st.spinner(
                    "Gemini is analyzing your video..."
                ):
                    result = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[
                            analysis_prompt,
                            video_part
                        ]
                    )

                # Display the result
                st.subheader("Analysis Result")

                if result.text:
                    st.markdown(result.text)
                else:
                    st.warning(
                        "Gemini returned no text. "
                        "Try a different question or video."
                    )

            except Exception as error:
                st.error(
                    f"An error occurred during analysis: {error}"
                )

            finally:
                # Clean up the local temporary video
                if video_path and os.path.exists(video_path):
                    os.remove(video_path)

else:
    st.info("Upload a video to begin your analysis.")

# Customize the question box
st.markdown(
    """
    <style>
    .stTextArea textarea {
        min-height: 100px;
    }
    </style>
    """,
    unsafe_allow_html=True
)
