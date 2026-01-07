# import os
# import base64
# import mimetypes
# import subprocess
# import csv
# import re
# import wave
# import struct
# from datetime import datetime
# from typing import Literal, Dict, Optional, List

# from openai import OpenAI
# from pydub import AudioSegment
# from sarvamai import SarvamAI


# # =========================
# # CONFIGURATION
# # =========================
# def get_output_base_path():
#     """Get output path - tries Desktop first, falls back to current directory"""
#     try:
#         desktop = os.path.join(os.path.expanduser("~"), "Desktop", "output")
#         os.makedirs(desktop, exist_ok=True)
#         return desktop
#     except Exception as e:
#         print(f"⚠️ Could not access Desktop, using local 'output' folder: {e}")
#         fallback = os.path.join(os.getcwd(), "output")
#         os.makedirs(fallback, exist_ok=True)
#         return fallback


# OUTPUT_BASE_PATH = get_output_base_path()

# TELUGU_DIGITS = {
#     '0': '౦', '1': '౧', '2': '౨', '3': '౩', '4': '౪',
#     '5': '౫', '6': '౬', '7': '౭', '8': '౮', '9': '౯'
# }

# TV_COMMAND_TYPES = {
#     "BREAKING NEWS": {
#         "icon": "🚨", "color": "#ff4444",
#         "sample_opening": "ఈ గంటలో మీకు బ్రేకింగ్ న్యూస్...",
#         "voice_tone": "Urgent, dramatic"
#     },
#     "LIVE REPORT": {
#         "icon": "📡", "color": "#ffaa00",
#         "sample_opening": "శుభసాయంత్రం, నేను ప్రత్యక్ష ప్రసారంలో...",
#         "voice_tone": "Present tense, energetic"
#     },
#     "HEADLINE NEWS": {
#         "icon": "📰", "color": "#44aaff",
#         "sample_opening": "ఈ రాత్రి టాప్ స్టోరీలు ఇవి...",
#         "voice_tone": "Clear, professional"
#     },
#     "SPORTS NEWS": {
#         "icon": "⚽", "color": "#00aa44",
#         "sample_opening": "ఈ రాత్రి స్పోర్ట్స్‌లో...",
#         "voice_tone": "Energetic, exciting"
#     },
#     "CRIME REPORT": {
#         "icon": "🚔", "color": "#333333",
#         "sample_opening": "పోలీసులు దర్యాప్తు చేస్తున్నారు...",
#         "voice_tone": "Serious, factual"
#     },
# }

# VOICE_PRESETS = {
#     "anushka": {"name": "Anushka", "gender": "Female", "style": "Clear & Professional"},
#     "vidya": {"name": "Vidya", "gender": "Female", "style": "General Purpose"},
#     "manisha": {"name": "Manisha", "gender": "Female", "style": "Educational"},
#     "arya": {"name": "Arya", "gender": "Female", "style": "News & Announcements"},
#     "meera": {"name": "Meera", "gender": "Female", "style": "Conversational"},
#     "kavya": {"name": "Kavya", "gender": "Female", "style": "Storytelling"},
#     "abhilash": {"name": "Abhilash", "gender": "Male", "style": "Authoritative"},
#     "karun": {"name": "Karun", "gender": "Male", "style": "Conversational"},
#     "hitesh": {"name": "Hitesh", "gender": "Male", "style": "General Purpose"}
# }


# # =========================
# # TTS FUNCTIONS
# # =========================
# def generate_audio_from_script(
#     script_text: str,
#     sarvam_api_key: str,
#     speaker: str = "arya",
#     pitch: float = 0.0,
#     pace: float = 1.0,
#     loudness: float = 1.0,
#     sample_rate: int = 22050,
#     output_path: Optional[str] = None
# ) -> str:
#     """Generate audio from Telugu script using Sarvam AI"""
#     try:
#         client = SarvamAI(api_subscription_key=sarvam_api_key)
#         os.makedirs("temp_audio", exist_ok=True)
        
#         raw_chunks = re.split(r'(?<=[।\.\?\!])\s+', script_text.strip())
#         valid_chunks = [
#             chunk for chunk in raw_chunks
#             if len(chunk.strip()) > 3 and re.search(r'[\u0C00-\u0C7F]', chunk)
#         ]
        
#         chunk_files = []
        
#         for i, sentence in enumerate(valid_chunks):
#             response = client.text_to_speech.convert(
#                 text=sentence,
#                 target_language_code="te-IN",
#                 speaker=speaker,
#                 pitch=pitch,
#                 pace=pace,
#                 loudness=loudness,
#                 output_audio_codec="mp3",
#                 speech_sample_rate=sample_rate,
#                 enable_preprocessing=True,
#                 model="bulbul:v2"
#             )
            
#             chunk_name = f"temp_audio/chunk_{i}.mp3"
#             with open(chunk_name, "wb") as f:
#                 for audio_base64 in response.audios:
#                     f.write(base64.b64decode(audio_base64))
            
#             chunk_files.append(chunk_name)
        
#         combined = AudioSegment.empty()
#         for chunk in chunk_files:
#             combined += AudioSegment.from_mp3(chunk)
        
#         if not output_path:
#             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#             output_path = os.path.join(get_output_base_path(), f"audio_output_{timestamp}.mp3")
        
#         combined.export(output_path, format="mp3")
        
#         for chunk in chunk_files:
#             try:
#                 os.remove(chunk)
#             except:
#                 pass
#         try:
#             os.rmdir("temp_audio")
#         except:
#             pass
        
#         return output_path
        
#     except Exception as e:
#         raise RuntimeError(f"Audio generation failed: {str(e)}")


# # =========================
# # CSV LOGGING
# # =========================
# def ensure_csv_exists():
#     """Ensure CSV log file exists with headers"""
#     output_path = get_output_base_path()
#     csv_path = os.path.join(output_path, "processing_log.csv")

#     if not os.path.exists(csv_path):
#         with open(csv_path, 'w', newline='', encoding='utf-8') as f:
#             writer = csv.writer(f)
#             writer.writerow([
#                 'Date', 'Time', 'Source Type', 'Input File', 'Size (MB)',
#                 'Language', 'Format', 'Location', 'Time', 'AI Model',
#                 'Output Files', 'Audio Generated', 'Status', 'Notes'
#             ])


# def log_to_csv(source_type: str, input_file_name: Optional[str],
#                input_file_size_mb: float, languages: List[str], news_format: str,
#                location: Optional[str], incident_time: Optional[str], ai_model: str,
#                output_files: List[str], audio_generated: bool = False,
#                status: str = "SUCCESS", notes: str = ""):
#     """Log processing to CSV"""
#     ensure_csv_exists()
#     output_path = get_output_base_path()
#     csv_path = os.path.join(output_path, "processing_log.csv")

#     now = datetime.now()
#     with open(csv_path, 'a', newline='', encoding='utf-8') as f:
#         writer = csv.writer(f)
#         writer.writerow([
#             now.strftime("%d-%m-%Y"), now.strftime("%H:%M:%S"),
#             source_type, input_file_name or "N/A", f"{input_file_size_mb:.2f}",
#             " | ".join(languages), news_format, location or "N/A",
#             incident_time or "N/A", ai_model,
#             " | ".join([os.path.basename(f) for f in output_files]),
#             "Yes" if audio_generated else "No",
#             status, notes
#         ])


# # =========================
# # UTILITY FUNCTIONS
# # =========================
# def ensure_dirs():
#     """Create necessary directories"""
#     os.makedirs("temp", exist_ok=True)


# def make_client(api_key: str) -> OpenAI:
#     """Create OpenAI client"""
#     return OpenAI(api_key=api_key)


# def get_optimal_model(source_type: str, commands: List[str], file_size_mb: float = 0) -> str:
#     """Auto-select best model"""
#     if source_type in ["image", "video"] or "CRIME REPORT" in commands or file_size_mb > 50:
#         return "gpt-4o"
#     return "gpt-4o-mini"


# def save_upload_to_temp(uploaded_file) -> str:
#     """Save uploaded file to temp directory"""
#     ensure_dirs()
#     ext = os.path.splitext(uploaded_file.name)[1]
#     path = os.path.join("temp", f"upload_{int(datetime.now().timestamp())}{ext}")
#     with open(path, "wb") as f:
#         f.write(uploaded_file.getbuffer())
#     return path


# def convert_to_telugu_numbers(text: str) -> str:
#     """Convert English numbers to Telugu"""
#     for eng, tel in TELUGU_DIGITS.items():
#         text = text.replace(eng, tel)
#     return text.replace('...', '…')


# def file_to_data_url(file_path: str) -> str:
#     """Convert file to base64 data URL"""
#     mime, _ = mimetypes.guess_type(file_path)
#     with open(file_path, "rb") as f:
#         b64 = base64.b64encode(f.read()).decode("utf-8")
#     return f"data:{mime or 'application/octet-stream'};base64,{b64}"


# # =========================
# # VIDEO/AUDIO PROCESSING
# # =========================
# def create_silent_audio(output_path: str, duration: float = 1.0):
#     """Create a silent audio file as fallback"""
#     try:
#         os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        
#         cmd = [
#             "ffmpeg", "-y",
#             "-f", "lavfi",
#             "-i", "anullsrc=r=16000:cl=mono",
#             "-t", str(duration),
#             "-acodec", "pcm_s16le",
#             "-ar", "16000", "-ac", "1",
#             "-loglevel", "error",
#             output_path
#         ]
        
#         result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
#         if result.returncode != 0:
#             raise Exception(f"Silent audio generation failed: {result.stderr}")
            
#     except Exception:
#         # If FFmpeg fails, create minimal WAV file manually
#         try:
#             with wave.open(output_path, 'wb') as wav:
#                 wav.setnchannels(1)  # Mono
#                 wav.setsampwidth(2)  # 16-bit
#                 wav.setframerate(16000)
#                 silence = struct.pack('<h', 0) * 16000
#                 wav.writeframes(silence)
#         except Exception as e:
#             print(f"Failed to create silent audio: {e}")


# def extract_audio_from_video(video_path: str, out_wav_path: str) -> None:
#     """Extract audio using ffmpeg with robust error handling"""
#     try:
#         # Ensure output directory exists
#         out_dir = os.path.dirname(out_wav_path)
#         if out_dir:
#             os.makedirs(out_dir, exist_ok=True)
        
#         # First, check if video has audio stream
#         probe_cmd = [
#             "ffprobe", "-v", "error",
#             "-select_streams", "a:0",
#             "-show_entries", "stream=codec_type",
#             "-of", "default=noprint_wrappers=1:nokey=1",
#             video_path
#         ]
        
#         probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
        
#         if probe_result.returncode != 0 or not probe_result.stdout.strip():
#             # Video has no audio stream - create silent audio
#             create_silent_audio(out_wav_path, duration=1.0)
#             raise RuntimeError("Video file has no audio stream")
        
#         # Extract audio
#         cmd = [
#             "ffmpeg", "-y", "-i", video_path,
#             "-vn", "-acodec", "pcm_s16le",
#             "-ar", "16000", "-ac", "1",
#             "-loglevel", "error",
#             out_wav_path
#         ]
        
#         result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
#         if result.returncode != 0:
#             raise RuntimeError(f"FFmpeg extraction failed: {result.stderr}")
        
#         # Verify output file was created
#         if not os.path.exists(out_wav_path) or os.path.getsize(out_wav_path) == 0:
#             raise RuntimeError("Audio extraction produced empty file")
            
#     except subprocess.TimeoutExpired:
#         raise RuntimeError("FFmpeg timeout - video processing took too long")
#     except FileNotFoundError:
#         raise RuntimeError("FFmpeg not found. Please install ffmpeg and add to PATH")


# def transcribe_audio(client: OpenAI, audio_path: str, language_hint: Optional[str] = None) -> str:
#     """Transcribe audio using Whisper"""
#     with open(audio_path, "rb") as f:
#         resp = client.audio.transcriptions.create(
#             model="whisper-1", file=f,
#             language=language_hint, response_format="text"
#         )
#     return resp


# def extract_video_frames(video_path: str, num_frames: int = 5) -> List[str]:
#     """Extract frames from video"""
#     ensure_dirs()

#     cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
#            "-of", "default=noprint_wrappers=1:nokey=1", video_path]
#     result = subprocess.run(cmd, capture_output=True, text=True)
#     duration = float(result.stdout.strip())

#     frame_paths = []
#     for i in range(num_frames):
#         timestamp = (duration / (num_frames + 1)) * (i + 1)
#         frame_path = os.path.join("temp", f"frame_{int(datetime.now().timestamp())}_{i}.jpg")

#         cmd = ["ffmpeg", "-y", "-ss", str(timestamp), "-i", video_path,
#                "-vframes", "1", "-q:v", "2", "-loglevel", "error", frame_path]
#         subprocess.run(cmd, capture_output=True)

#         if os.path.exists(frame_path):
#             frame_paths.append(frame_path)

#     return frame_paths


# # =========================
# # AI ANALYSIS
# # =========================
# def deep_analyze_image(client: OpenAI, image_data_url: str) -> str:
#     """Deep AI analysis of image for news understanding"""
#     analysis_prompt = """Analyze this image for TV news reporting.

# Cover:
# 1. MAIN EVENT - What is happening?
# 2. PEOPLE - Who is visible?
# 3. LOCATION - Where is this?
# 4. NEWS ANGLE - What type of story?
# 5. KEY FACTS - Important details

# Be detailed and specific."""

#     try:
#         response = client.chat.completions.create(
#             model="gpt-4o",
#             messages=[{
#                 "role": "user",
#                 "content": [
#                     {"type": "text", "text": analysis_prompt},
#                     {"type": "image_url", "image_url": {"url": image_data_url, "detail": "high"}}
#                 ]
#             }],
#             max_tokens=2000,
#             temperature=0.2
#         )
#         return response.choices[0].message.content
#     except Exception as e:
#         raise RuntimeError(f"Image analysis failed: {str(e)}")


# def deep_analyze_video(client: OpenAI, video_path: str) -> str:
#     """Analyze video by extracting and analyzing frames"""
#     frame_paths = extract_video_frames(video_path, num_frames=5)
#     if not frame_paths:
#         return "Unable to analyze video"

#     content = [{"type": "text", "text": """Analyze these video frames for TV news.
# Cover: NARRATIVE, PEOPLE, LOCATION, NEWS VALUE. Be detailed."""}]

#     for i, frame_path in enumerate(frame_paths):
#         content.append({"type": "text", "text": f"\nFrame {i+1}:"})
#         content.append({"type": "image_url", "image_url": {
#             "url": file_to_data_url(frame_path), "detail": "high"
#         }})

#     response = client.chat.completions.create(
#         model="gpt-4o",
#         messages=[{"role": "user", "content": content}],
#         max_tokens=2500, temperature=0.3
#     )

#     for frame in frame_paths:
#         try:
#             os.remove(frame)
#         except:
#             pass

#     return response.choices[0].message.content


# def auto_detect_news_type(content: str, client: OpenAI) -> List[str]:
#     """Auto-detect news type from content"""
#     prompt = f"""Based on this content, return ONLY ONE news type from:
# BREAKING NEWS, LIVE REPORT, HEADLINE NEWS, SPORTS NEWS, CRIME REPORT

# Content: {content[:1000]}

# Return just the type name, nothing else."""

#     try:
#         response = client.chat.completions.create(
#             model="gpt-4o-mini",
#             messages=[{"role": "user", "content": prompt}],
#             max_tokens=20, temperature=0.1
#         )
#         detected = response.choices[0].message.content.strip()
#         return [detected] if detected in TV_COMMAND_TYPES else ["HEADLINE NEWS"]
#     except:
#         return ["HEADLINE NEWS"]


# # =========================
# # SCRIPT GENERATION
# # =========================
# def clean_script(script: str) -> str:
#     """Clean script output"""
#     skip_patterns = ['=', '---', '**', '##', '[', 'LANGUAGE:', 'SCRIPT', '📺', '🎯']
#     lines = [line.strip() for line in script.split('\n')
#              if line.strip() and len(line.strip()) > 5
#              and not any(p in line for p in skip_patterns)]
#     return '\n\n'.join(lines)


# def generate_tv_news_script_multilingual(
#     client: OpenAI, model: str, source_type: str,
#     command_types: List[str], languages: List[str], *,
#     raw_text: Optional[str] = None, transcript: Optional[str] = None,
#     content_analysis: Optional[str] = None, town: Optional[str] = None,
#     incident_time: Optional[str] = None, **kwargs
# ) -> Dict[str, str]:
#     """Generate Telugu TV news script"""

#     main_command = command_types[0] if command_types else "HEADLINE NEWS"
#     cmd_info = TV_COMMAND_TYPES.get(main_command, TV_COMMAND_TYPES["HEADLINE NEWS"])

#     system_prompt = f"""You are a Telugu TV news anchor writing a {main_command} script.

# Sample Opening: "{cmd_info['sample_opening']}"
# Voice Tone: {cmd_info['voice_tone']}

# RULES:
# 1. Write EXACTLY what anchor says in Telugu
# 2. Natural conversational Telugu
# 3. ALL numbers in Telugu numerals (౦౧౨౩౪౫౬౭౮౯)
# 4. NO bullet points, headers, or technical markers
# 5. Continuous narrative only

# Write ONLY the anchor's Telugu script."""

#     parts = []
#     if town or incident_time:
#         ctx = []
#         if town:
#             ctx.append(f"Location: {town}")
#         if incident_time:
#             ctx.append(f"Time: {incident_time}")
#         parts.append(f"CONTEXT: {', '.join(ctx)}\n")

#     if content_analysis:
#         parts.append(f"ANALYSIS:\n{content_analysis}\n")
#     if transcript:
#         parts.append(f"TRANSCRIPT:\n{transcript}\n")
#     if raw_text:
#         parts.append(f"INFO:\n{raw_text}\n")

#     parts.append(f"Write complete Telugu {main_command} script now.")

#     response = client.chat.completions.create(
#         model=model,
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": "\n".join(parts)}
#         ],
#         temperature=0.5, max_tokens=3000
#     )

#     script = clean_script(response.choices[0].message.content)
#     script = convert_to_telugu_numbers(script)

#     return {"te": script}


# def save_tv_script_output_multilingual(scripts: Dict[str, str],
#                                        source_type: str,
#                                        command_types: List[str]) -> Dict[str, str]:
#     """Save scripts to output folder"""
#     output_path = get_output_base_path()
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

#     prefix_map = {"image": "img", "video": "video", "audio": "audio", "text": "txt"}
#     prefix = prefix_map.get(source_type, source_type)

#     saved = {}
#     for lang, script in scripts.items():
#         filename = f"{prefix}_output_{timestamp}.txt"
#         path = os.path.join(output_path, filename)
#         with open(path, "w", encoding="utf-8") as f:
#             f.write(script)
#         saved[lang] = path

#     return saved


# def display_tv_script_multilingual(scripts: Dict[str, str],
#                                    command_types: List[str],
#                                    model_used: str):
#     """Display scripts in Streamlit"""
#     import streamlit as st

#     st.markdown(f"### 🤖 AI Model: `{model_used}`")

#     if command_types and command_types[0] in TV_COMMAND_TYPES:
#         info = TV_COMMAND_TYPES[command_types[0]]
#         st.markdown(f"""
#         <div style="background-color: {info['color']}20; border-left: 4px solid {info['color']};
#                     padding: 15px; border-radius: 5px; margin: 10px 0;">
#         <h3>{info['icon']} {command_types[0]}</h3>
#         <p><strong>Tone:</strong> {info['voice_tone']}</p>
#         </div>
#         """, unsafe_allow_html=True)

#     st.divider()

#     if "te" in scripts:
#         st.markdown("### 🇮🇳 Telugu News Script")
#         st.markdown(f"""
#         <style>
#         .telugu-script {{
#             font-family: 'Nirmala UI', 'Gautami', sans-serif;
#             font-size: 18px; line-height: 1.8;
#             background-color: #f8f9fa; padding: 20px;
#             border-radius: 8px; white-space: pre-wrap;
#         }}
#         </style>
#         <div class="telugu-script">{scripts["te"]}</div>
#         """, unsafe_allow_html=True)






# shared_components.py
import os
import base64
import mimetypes
import subprocess
import csv
import re
import wave
import struct
from datetime import datetime
from typing import Literal, Dict, Optional, List

from openai import OpenAI
from pydub import AudioSegment
from sarvamai import SarvamAI


# =========================
# CONFIGURATION
# =========================
def get_output_base_path():
    """Get output path - tries Desktop first, falls back to current directory"""
    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop", "output")
        os.makedirs(desktop, exist_ok=True)
        return desktop
    except Exception as e:
        print(f"⚠️ Could not access Desktop, using local 'output' folder: {e}")
        fallback = os.path.join(os.getcwd(), "output")
        os.makedirs(fallback, exist_ok=True)
        return fallback


OUTPUT_BASE_PATH = get_output_base_path()

TELUGU_DIGITS = {
    '0': '౦', '1': '౧', '2': '౨', '3': '౩', '4': '౪',
    '5': '౫', '6': '౬', '7': '౭', '8': '౮', '9': '౯'
}

TV_COMMAND_TYPES = {
    "BREAKING NEWS": {
        "icon": "🚨", "color": "#ff4444",
        "sample_opening": "ఈ గంటలో మీకు బ్రేకింగ్ న్యూస్...",
        "voice_tone": "Urgent, dramatic"
    },
    "LIVE REPORT": {
        "icon": "📡", "color": "#ffaa00",
        "sample_opening": "శుభసాయంత్రం, నేను ప్రత్యక్ష ప్రసారంలో...",
        "voice_tone": "Present tense, energetic"
    },
    "HEADLINE NEWS": {
        "icon": "📰", "color": "#44aaff",
        "sample_opening": "ఈ రాత్రి టాప్ స్టోరీలు ఇవి...",
        "voice_tone": "Clear, professional"
    },
    "SPORTS NEWS": {
        "icon": "⚽", "color": "#00aa44",
        "sample_opening": "ఈ రాత్రి స్పోర్ట్స్‌లో...",
        "voice_tone": "Energetic, exciting"
    },
    "CRIME REPORT": {
        "icon": "🚔", "color": "#333333",
        "sample_opening": "పోలీసులు దర్యాప్తు చేస్తున్నారు...",
        "voice_tone": "Serious, factual"
    },
}

VOICE_PRESETS = {
    "anushka": {"name": "Anushka", "gender": "Female", "style": "Clear & Professional"},
    "vidya": {"name": "Vidya", "gender": "Female", "style": "General Purpose"},
    "manisha": {"name": "Manisha", "gender": "Female", "style": "Educational"},
    "arya": {"name": "Arya", "gender": "Female", "style": "News & Announcements"},
    "meera": {"name": "Meera", "gender": "Female", "style": "Conversational"},
    "kavya": {"name": "Kavya", "gender": "Female", "style": "Storytelling"},
    "abhilash": {"name": "Abhilash", "gender": "Male", "style": "Authoritative"},
    "karun": {"name": "Karun", "gender": "Male", "style": "Conversational"},
    "hitesh": {"name": "Hitesh", "gender": "Male", "style": "General Purpose"}
}


# =========================
# TTS FUNCTIONS
# =========================
def generate_audio_from_script(
    script_text: str,
    sarvam_api_key: str,
    speaker: str = "arya",
    pitch: float = 0.0,
    pace: float = 1.0,
    loudness: float = 1.0,
    sample_rate: int = 22050,
    output_path: Optional[str] = None
) -> str:
    """Generate audio from Telugu script using Sarvam AI"""
    try:
        client = SarvamAI(api_subscription_key=sarvam_api_key)
        os.makedirs("temp_audio", exist_ok=True)
        
        raw_chunks = re.split(r'(?<=[।\.\?\!])\s+', script_text.strip())
        valid_chunks = [
            chunk for chunk in raw_chunks
            if len(chunk.strip()) > 3 and re.search(r'[\u0C00-\u0C7F]', chunk)
        ]
        
        chunk_files = []
        
        for i, sentence in enumerate(valid_chunks):
            response = client.text_to_speech.convert(
                text=sentence,
                target_language_code="te-IN",
                speaker=speaker,
                pitch=pitch,
                pace=pace,
                loudness=loudness,
                output_audio_codec="mp3",
                speech_sample_rate=sample_rate,
                enable_preprocessing=True,
                model="bulbul:v2"
            )
            
            chunk_name = f"temp_audio/chunk_{i}.mp3"
            with open(chunk_name, "wb") as f:
                for audio_base64 in response.audios:
                    f.write(base64.b64decode(audio_base64))
            
            chunk_files.append(chunk_name)
        
        combined = AudioSegment.empty()
        for chunk in chunk_files:
            combined += AudioSegment.from_mp3(chunk)
        
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(get_output_base_path(), f"audio_output_{timestamp}.mp3")
        
        combined.export(output_path, format="mp3")
        
        for chunk in chunk_files:
            try:
                os.remove(chunk)
            except:
                pass
        try:
            os.rmdir("temp_audio")
        except:
            pass
        
        return output_path
        
    except Exception as e:
        raise RuntimeError(f"Audio generation failed: {str(e)}")


# =========================
# CSV LOGGING
# =========================
def ensure_csv_exists():
    """Ensure CSV log file exists with headers"""
    output_path = get_output_base_path()
    csv_path = os.path.join(output_path, "processing_log.csv")

    if not os.path.exists(csv_path):
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Date', 'Time', 'Source Type', 'Input File', 'Size (MB)',
                'Language', 'Format', 'Location', 'Time', 'AI Model',
                'Output Files', 'Audio Generated', 'Status', 'Notes'
            ])


def log_to_csv(source_type: str, input_file_name: Optional[str],
               input_file_size_mb: float, languages: List[str], news_format: str,
               location: Optional[str], incident_time: Optional[str], ai_model: str,
               output_files: List[str], audio_generated: bool = False,
               status: str = "SUCCESS", notes: str = ""):
    """Log processing to CSV"""
    ensure_csv_exists()
    output_path = get_output_base_path()
    csv_path = os.path.join(output_path, "processing_log.csv")

    now = datetime.now()
    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            now.strftime("%d-%m-%Y"), now.strftime("%H:%M:%S"),
            source_type, input_file_name or "N/A", f"{input_file_size_mb:.2f}",
            " | ".join(languages), news_format, location or "N/A",
            incident_time or "N/A", ai_model,
            " | ".join([os.path.basename(f) for f in output_files]),
            "Yes" if audio_generated else "No",
            status, notes
        ])


# =========================
# UTILITY FUNCTIONS
# =========================
def ensure_dirs():
    """Create necessary directories"""
    os.makedirs("temp", exist_ok=True)


def make_client(api_key: str) -> OpenAI:
    """Create OpenAI client"""
    return OpenAI(api_key=api_key)


def get_optimal_model(source_type: str, commands: List[str], file_size_mb: float = 0) -> str:
    """Auto-select best model"""
    if source_type in ["image", "video"] or "CRIME REPORT" in commands or file_size_mb > 50:
        return "gpt-4o"
    return "gpt-4o-mini"


def save_upload_to_temp(file_path: str, file_data: bytes) -> str:
    """Save file data to temp directory"""
    ensure_dirs()
    ext = os.path.splitext(file_path)[1]
    path = os.path.join("temp", f"upload_{int(datetime.now().timestamp())}{ext}")
    with open(path, "wb") as f:
        f.write(file_data)
    return path


def convert_to_telugu_numbers(text: str) -> str:
    """Convert English numbers to Telugu"""
    for eng, tel in TELUGU_DIGITS.items():
        text = text.replace(eng, tel)
    return text.replace('...', '…')


def file_to_data_url(file_path: str) -> str:
    """Convert file to base64 data URL"""
    mime, _ = mimetypes.guess_type(file_path)
    with open(file_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime or 'application/octet-stream'};base64,{b64}"


# =========================
# VIDEO/AUDIO PROCESSING
# =========================
def create_silent_audio(output_path: str, duration: float = 1.0):
    """Create a silent audio file as fallback"""
    try:
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "anullsrc=r=16000:cl=mono",
            "-t", str(duration),
            "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            "-loglevel", "error",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            raise Exception(f"Silent audio generation failed: {result.stderr}")
            
    except Exception:
        try:
            with wave.open(output_path, 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                silence = struct.pack('<h', 0) * 16000
                wav.writeframes(silence)
        except Exception as e:
            print(f"Failed to create silent audio: {e}")


def extract_audio_from_video(video_path: str, out_wav_path: str) -> None:
    """Extract audio using ffmpeg with robust error handling"""
    try:
        out_dir = os.path.dirname(out_wav_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_type",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
        
        if probe_result.returncode != 0 or not probe_result.stdout.strip():
            create_silent_audio(out_wav_path, duration=1.0)
            raise RuntimeError("Video file has no audio stream")
        
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            "-loglevel", "error",
            out_wav_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg extraction failed: {result.stderr}")
        
        if not os.path.exists(out_wav_path) or os.path.getsize(out_wav_path) == 0:
            raise RuntimeError("Audio extraction produced empty file")
            
    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg timeout - video processing took too long")
    except FileNotFoundError:
        raise RuntimeError("FFmpeg not found. Please install ffmpeg and add to PATH")


def transcribe_audio(client: OpenAI, audio_path: str, language_hint: Optional[str] = None) -> str:
    """Transcribe audio using Whisper"""
    with open(audio_path, "rb") as f:
        resp = client.audio.transcriptions.create(
            model="whisper-1", file=f,
            language=language_hint, response_format="text"
        )
    return resp


def extract_video_frames(video_path: str, num_frames: int = 5) -> List[str]:
    """Extract frames from video"""
    ensure_dirs()

    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", video_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = float(result.stdout.strip())

    frame_paths = []
    for i in range(num_frames):
        timestamp = (duration / (num_frames + 1)) * (i + 1)
        frame_path = os.path.join("temp", f"frame_{int(datetime.now().timestamp())}_{i}.jpg")

        cmd = ["ffmpeg", "-y", "-ss", str(timestamp), "-i", video_path,
               "-vframes", "1", "-q:v", "2", "-loglevel", "error", frame_path]
        subprocess.run(cmd, capture_output=True)

        if os.path.exists(frame_path):
            frame_paths.append(frame_path)

    return frame_paths


# =========================
# AI ANALYSIS
# =========================
def deep_analyze_image(client: OpenAI, image_data_url: str) -> str:
    """Deep AI analysis of image for news understanding"""
    analysis_prompt = """Analyze this image for TV news reporting.

Cover:
1. MAIN EVENT - What is happening?
2. PEOPLE - Who is visible?
3. LOCATION - Where is this?
4. NEWS ANGLE - What type of story?
5. KEY FACTS - Important details

Be detailed and specific."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": analysis_prompt},
                    {"type": "image_url", "image_url": {"url": image_data_url, "detail": "high"}}
                ]
            }],
            max_tokens=2000,
            temperature=0.2
        )
        return response.choices[0].message.content
    except Exception as e:
        raise RuntimeError(f"Image analysis failed: {str(e)}")


def deep_analyze_video(client: OpenAI, video_path: str) -> str:
    """Analyze video by extracting and analyzing frames"""
    frame_paths = extract_video_frames(video_path, num_frames=5)
    if not frame_paths:
        return "Unable to analyze video"

    content = [{"type": "text", "text": """Analyze these video frames for TV news.
Cover: NARRATIVE, PEOPLE, LOCATION, NEWS VALUE. Be detailed."""}]

    for i, frame_path in enumerate(frame_paths):
        content.append({"type": "text", "text": f"\nFrame {i+1}:"})
        content.append({"type": "image_url", "image_url": {
            "url": file_to_data_url(frame_path), "detail": "high"
        }})

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": content}],
        max_tokens=2500, temperature=0.3
    )

    for frame in frame_paths:
        try:
            os.remove(frame)
        except:
            pass

    return response.choices[0].message.content


def auto_detect_news_type(content: str, client: OpenAI) -> List[str]:
    """Auto-detect news type from content"""
    prompt = f"""Based on this content, return ONLY ONE news type from:
BREAKING NEWS, LIVE REPORT, HEADLINE NEWS, SPORTS NEWS, CRIME REPORT

Content: {content[:1000]}

Return just the type name, nothing else."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20, temperature=0.1
        )
        detected = response.choices[0].message.content.strip()
        return [detected] if detected in TV_COMMAND_TYPES else ["HEADLINE NEWS"]
    except:
        return ["HEADLINE NEWS"]


# =========================
# SCRIPT GENERATION
# =========================
def clean_script(script: str) -> str:
    """Clean script output"""
    skip_patterns = ['=', '---', '**', '##', '[', 'LANGUAGE:', 'SCRIPT', '📺', '🎯']
    lines = [line.strip() for line in script.split('\n')
             if line.strip() and len(line.strip()) > 5
             and not any(p in line for p in skip_patterns)]
    return '\n\n'.join(lines)


def generate_tv_news_script_multilingual(
    client: OpenAI, model: str, source_type: str,
    command_types: List[str], languages: List[str], *,
    raw_text: Optional[str] = None, transcript: Optional[str] = None,
    content_analysis: Optional[str] = None, town: Optional[str] = None,
    incident_time: Optional[str] = None, **kwargs
) -> Dict[str, str]:
    """Generate Telugu TV news script"""

    main_command = command_types[0] if command_types else "HEADLINE NEWS"
    cmd_info = TV_COMMAND_TYPES.get(main_command, TV_COMMAND_TYPES["HEADLINE NEWS"])

    system_prompt = f"""You are a Telugu TV news anchor writing a {main_command} script.

Sample Opening: "{cmd_info['sample_opening']}"
Voice Tone: {cmd_info['voice_tone']}

RULES:
1. Write EXACTLY what anchor says in Telugu
2. Natural conversational Telugu
3. ALL numbers in Telugu numerals (౦౧౨౩౪౫౬౭౮౯)
4. NO bullet points, headers, or technical markers
5. Continuous narrative only

Write ONLY the anchor's Telugu script."""

    parts = []
    if town or incident_time:
        ctx = []
        if town:
            ctx.append(f"Location: {town}")
        if incident_time:
            ctx.append(f"Time: {incident_time}")
        parts.append(f"CONTEXT: {', '.join(ctx)}\n")

    if content_analysis:
        parts.append(f"ANALYSIS:\n{content_analysis}\n")
    if transcript:
        parts.append(f"TRANSCRIPT:\n{transcript}\n")
    if raw_text:
        parts.append(f"INFO:\n{raw_text}\n")

    parts.append(f"Write complete Telugu {main_command} script now.")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "\n".join(parts)}
        ],
        temperature=0.5, max_tokens=3000
    )

    script = clean_script(response.choices[0].message.content)
    script = convert_to_telugu_numbers(script)

    return {"te": script}


def save_tv_script_output_multilingual(scripts: Dict[str, str],
                                       source_type: str,
                                       command_types: List[str]) -> Dict[str, str]:
    """Save scripts to output folder"""
    output_path = get_output_base_path()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    prefix_map = {"image": "img", "video": "video", "audio": "audio", "text": "txt"}
    prefix = prefix_map.get(source_type, source_type)

    saved = {}
    for lang, script in scripts.items():
        filename = f"{prefix}_output_{timestamp}.txt"
        path = os.path.join(output_path, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(script)
        saved[lang] = path

    return saved

def get_video_duration(video_path):
    """Get video duration in seconds using ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except:
        pass
    
    # Fallback: estimate from file size
    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    return min(file_size_mb * 5, 600)

def generate_tv_news_script_multilingual_with_duration(
    client: OpenAI, model: str, source_type: str,
    command_types: List[str], languages: List[str],
    target_duration_seconds: int = 30,  # NEW PARAMETER
    *,
    raw_text: Optional[str] = None, transcript: Optional[str] = None,
    content_analysis: Optional[str] = None, town: Optional[str] = None,
    incident_time: Optional[str] = None, **kwargs
) -> Dict[str, str]:
    """Generate Telugu TV news script with duration constraint"""

    main_command = command_types[0] if command_types else "HEADLINE NEWS"
    cmd_info = TV_COMMAND_TYPES.get(main_command, TV_COMMAND_TYPES["HEADLINE NEWS"])
    
    # Calculate approximate word count for target duration
    # Telugu TTS: ~3-4 words per second (conservative estimate)
    target_words = int(target_duration_seconds * 3.5)

    system_prompt = f"""You are a Telugu TV news anchor writing a {main_command} script.

CRITICAL CONSTRAINTS:
- Script duration: MAXIMUM {target_duration_seconds} seconds when spoken
- Target word count: ~{target_words} words in Telugu
- This is STRICT - script must be concise and fit within {target_duration_seconds} seconds

Sample Opening: "{cmd_info['sample_opening']}"
Voice Tone: {cmd_info['voice_tone']}

RULES:
1. Write EXACTLY what anchor says in Telugu
2. Natural conversational Telugu
3. ALL numbers in Telugu numerals (౦౧౨౩౪౫౬౭౮౯)
4. NO bullet points, headers, or technical markers
5. Continuous narrative only
6. Keep it SHORT and CRISP - must fit in {target_duration_seconds} seconds
7. Only cover the MOST IMPORTANT points

Write ONLY the anchor's Telugu script - keep it under {target_words} words."""

    parts = []
    if town or incident_time:
        ctx = []
        if town:
            ctx.append(f"Location: {town}")
        if incident_time:
            ctx.append(f"Time: {incident_time}")
        parts.append(f"CONTEXT: {', '.join(ctx)}\n")

    if content_analysis:
        parts.append(f"ANALYSIS (summarize to key points only):\n{content_analysis[:800]}\n")
    if transcript:
        parts.append(f"TRANSCRIPT (extract essence only):\n{transcript[:800]}\n")
    if raw_text:
        parts.append(f"INFO (main points only):\n{raw_text[:500]}\n")

    parts.append(f"""Write a {target_duration_seconds}-second Telugu {main_command} script.
Remember: MAXIMUM {target_words} Telugu words. Be extremely concise.""")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "\n".join(parts)}
        ],
        temperature=0.3,  # Lower temperature for more concise output
        max_tokens=int(target_words * 3)  # Rough token estimate
    )

    script = clean_script(response.choices[0].message.content)
    script = convert_to_telugu_numbers(script)

    return {"te": script}