
import os
import time
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# ---------------- Page configuration ----------------
st.set_page_config(
    page_title="TalkToVideo - AI Video Summarizer",
    page_icon="🎥",
    layout="wide"
)

st.title("TalkToVideo 🎥🧠💬")
st.header("AI Video Summarizer powered by Gemini")

# ---------------- API key configuration ----------------
try:
    API_KEY = st.secrets.get("GOOGLE_API_KEY", "")
except Exception:
    API_KEY = ""

if not API_KEY:
    API_KEY = os.getenv("GOOGLE_API_KEY", "")

if not API_KEY:
    st.error(
        "Google API key is missing. Add GOOGLE_API_KEY "
        "in Streamlit Settings > Secrets."
    )
    st.stop()

client = genai.Client(api_key=API_KEY)

# ---------------- Video uploader ----------------
video_file = st.file_uploader(
    "Upload your video",
    type=["mp4", "mov", "avi"],
    help="Upload a video smaller than 200 MB."
)

if video_file is not None:
    file_size_mb = video_file.size / (1024 * 1024)

    if file_size_mb > 200:
        st.error("Please upload a video smaller than 200 MB.")
        st.stop()

    st.video(video_file)

    user_query = st.text_area(
        "What insights are you seeking from the video?",
        placeholder="Summarize this video and explain the main points.",
        help="Ask a specific question about the video."
    )

    if st.button("🔍 Analyze Video", type="primary"):
        if not user_query.strip():
            st.warning("Please enter a question about the video.")
        else:
            video_path = None
            uploaded_video = None

            try:
                # Save uploaded video to a temporary file
                suffix = Path(video_file.name).suffix.lower() or ".mp4"

                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=suffix
                ) as temp_video:
                    temp_video.write(video_file.getvalue())
                    video_path = temp_video.name

                # Upload and wait for processing
                with st.spinner("Uploading and processing your video..."):
                    uploaded_video = client.files.upload(
                        file=video_path
                    )

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
                            "Try another supported video file."
                        )

                    if not uploaded_video.uri:
                        raise RuntimeError(
                            "Google did not return a video URI."
                        )

                # Prepare the video input
                video_part = types.Part.from_uri(
                    file_uri=uploaded_video.uri,
                    mime_type=uploaded_video.mime_type or "video/mp4"
                )

                analysis_prompt = f"""
You are an AI video analysis assistant.

Analyze the uploaded video and answer the user's question.

User question:
{user_query}

Instructions:
- Summarize the important events and key takeaways.
- Answer the user's question clearly and accurately.
- Use headings or bullet points where helpful.
- Do not invent details that are not supported by the video.
"""

                # Retry temporary Gemini availability errors
                result = None
                max_attempts = 4

                with st.spinner(
                    "Gemini is analyzing your video..."
                ):
                    for attempt in range(max_attempts):
                        try:
                            result = client.models.generate_content(
                                model="gemini-3.8-flash",
                                contents=[
                                    analysis_prompt,
                                    video_part
                                ]
                            )
                            break

                        except Exception as error:
                            error_message = str(error).upper()

                            temporary_error = any(
                                marker in error_message
                                for marker in [
                                    "503",
                                    "UNAVAILABLE",
                                    "429",
                                    "RESOURCE_EXHAUSTED",
                                    "500",
                                    "INTERNAL SERVER ERROR"
                                ]
                            )

                            if not temporary_error:
                                raise

                            if attempt == max_attempts - 1:
                                raise RuntimeError(
                                    "Gemini is still unavailable after "
                                    f"{max_attempts} attempts. Please try "
                                    "again later. Original error: "
                                    f"{error}"
                                ) from error

                            wait_seconds = 2 ** (attempt + 1)

                            st.warning(
                                "Gemini is temporarily busy. "
                                f"Retrying in {wait_seconds} seconds "
                                f"(attempt {attempt + 2} of "
                                f"{max_attempts})..."
                            )

                            time.sleep(wait_seconds)

                # Display the answer
                st.subheader("Analysis Result")

                if result is not None and result.text:
                    st.markdown(result.text)
                else:
                    st.warning(
                        "Gemini returned no text. Try another question "
                        "or a shorter video."
                    )

            except Exception as error:
                st.error(f"Video analysis failed: {error}")

            finally:
                # Clean up the local temporary file
                if video_path and os.path.exists(video_path):
                    try:
                        os.remove(video_path)
                    except OSError:
                        pass

else:
    st.info("Upload a video to begin your analysis.")

# ---------------- Styling ----------------
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
