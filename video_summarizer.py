# video_summarizer.py
import os
import json
import subprocess
import tempfile
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ============================================
# OUTPUT CONFIGURATION - Change this path
# ============================================
OUTPUT_FOLDER = r"C:\Users\GLOBAL T\Desktop\NewsBot\output"


def get_next_filename(folder, prefix="in", ext=".mp4"):
    """
    Find next available filename like in1.mp4, in2.mp4, in3.mp4...
    Also fills gaps - if in1, in3 exist, returns in2
    """
    os.makedirs(folder, exist_ok=True)
    
    # Find all existing numbers
    existing_numbers = set()
    for f in os.listdir(folder):
        if f.startswith(prefix) and f.endswith(ext):
            try:
                num = int(f[len(prefix):-len(ext)])
                existing_numbers.add(num)
            except ValueError:
                continue
    
    # Find first available number (fills gaps)
    i = 1
    while i in existing_numbers:
        i += 1
    
    return os.path.join(folder, f"{prefix}{i}{ext}")


def extract_audio(video_path, audio_path):
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vn', '-acodec', 'libmp3lame',
        '-ar', '16000', '-ac', '1',
        '-y', '-loglevel', 'error', audio_path
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise Exception("Audio extraction failed")
    return audio_path


def get_video_duration(video_path):
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except:
        return 0


def transcribe_audio_whisper(audio_path, api_key):
    client = OpenAI(api_key=api_key)
    with open(audio_path, 'rb') as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["segment"]
        )
    return transcript


def analyze_for_summary(transcript, api_key, target_duration):
    client = OpenAI(api_key=api_key)
    
    segments_text = "\n".join([
        f"[{seg.start:.2f}s - {seg.end:.2f}s]: {seg.text}"
        for seg in transcript.segments
    ])
    
    prompt = f"""Create a {target_duration}-second video summary.

TRANSCRIPT:
{segments_text}

Select 4-6 key segments totaling ~{target_duration} seconds with:
- Important content
- Clear speech
- Complete sentences

Return ONLY valid JSON:
[
  {{
    "start_time": 0.5,
    "end_time": 8.3,
    "reason": "Key point",
    "text": "segment text"
  }}
]"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a video editor. Return ONLY valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=2000
    )
    
    result = response.choices[0].message.content.strip()
    start_idx = result.find('[')
    end_idx = result.rfind(']')
    
    if start_idx != -1 and end_idx != -1:
        return json.loads(result[start_idx:end_idx+1])
    return []


def create_summary_video(input_video, segments, output_path):
    with tempfile.TemporaryDirectory() as temp_dir:
        segment_files = []
        
        for i, seg in enumerate(segments):
            segment_path = os.path.join(temp_dir, f"seg_{i:03d}.mp4")
            duration = seg['end_time'] - seg['start_time']
            
            cmd = [
                'ffmpeg', '-ss', str(seg['start_time']),
                '-i', input_video,
                '-t', str(duration),
                '-c:v', 'libx264', '-preset', 'fast',
                '-c:a', 'aac',
                '-y', '-loglevel', 'error', segment_path
            ]
            subprocess.run(cmd, timeout=60)
            segment_files.append(segment_path)
        
        concat_file = os.path.join(temp_dir, 'concat.txt')
        with open(concat_file, 'w', encoding='utf-8') as f:
            for seg_file in segment_files:
                f.write(f"file '{seg_file}'\n")
        
        cmd = [
            'ffmpeg', '-f', 'concat', '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',
            '-y', '-loglevel', 'error', output_path
        ]
        subprocess.run(cmd, timeout=120)
    
    return output_path


def summarize_video_to_30sec(video_path, target_duration=30):
    """
    Summarize video to 30 seconds (or specified duration)
    Returns the summarized video path for further processing
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise RuntimeError("OPENAI_API_KEY not found")
    
    print(f"🎬 Summarizing video to {target_duration}s...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        video_duration = get_video_duration(video_path)
        
        if video_duration <= target_duration:
            print(f"⚠️ Video already {video_duration:.1f}s, no summarization needed")
            return {
                'summary_video_path': video_path,
                'original_duration': video_duration,
                'summary_duration': video_duration,
                'was_summarized': False
            }
        
        # Extract and transcribe
        audio_path = os.path.join(temp_dir, "audio.mp3")
        extract_audio(video_path, audio_path)
        
        transcript = transcribe_audio_whisper(audio_path, openai_key)
        segments = analyze_for_summary(transcript, openai_key, target_duration)
        
        if not segments:
            raise ValueError("No segments found for summarization")
        
        # Create summary in temp directory
        summary_path = os.path.join(temp_dir, "summary.mp4")
        create_summary_video(video_path, segments, summary_path)
        
        # ============================================
        # AUTO-INCREMENT NAMING - in1.mp4, in2.mp4...
        # ============================================
        final_summary_path = get_next_filename(OUTPUT_FOLDER, prefix="in", ext=".mp4")
        
        import shutil
        shutil.copy2(summary_path, final_summary_path)
        
        summary_duration = sum(s['end_time'] - s['start_time'] for s in segments)
        
        print(f"✅ Summarized: {video_duration:.1f}s → {summary_duration:.1f}s")
        print(f"💾 Saved to: {final_summary_path}")
        
        return {
            'summary_video_path': final_summary_path,
            'original_duration': video_duration,
            'summary_duration': summary_duration,
            'was_summarized': True,
            'segments_count': len(segments),
            'output_filename': os.path.basename(final_summary_path)
        }


# ============================================
# TEST FUNCTION
# ============================================
if __name__ == "__main__":
    print(f"📁 Output folder: {OUTPUT_FOLDER}")
    print(f"📄 Next file would be: {get_next_filename(OUTPUT_FOLDER, 'in', '.mp4')}")


# # video_summarizer.py
# import os
# import json
# import subprocess
# import tempfile
# from datetime import datetime
# from openai import OpenAI
# from dotenv import load_dotenv

# load_dotenv()

# def extract_audio(video_path, audio_path):
#     cmd = [
#         'ffmpeg', '-i', video_path,
#         '-vn', '-acodec', 'libmp3lame',
#         '-ar', '16000', '-ac', '1',
#         '-y', '-loglevel', 'error', audio_path
#     ]
#     result = subprocess.run(cmd, capture_output=True)
#     if result.returncode != 0:
#         raise Exception("Audio extraction failed")
#     return audio_path

# def get_video_duration(video_path):
#     cmd = [
#         'ffprobe', '-v', 'error',
#         '-show_entries', 'format=duration',
#         '-of', 'default=noprint_wrappers=1:nokey=1',
#         video_path
#     ]
#     result = subprocess.run(cmd, capture_output=True, text=True)
#     try:
#         return float(result.stdout.strip())
#     except:
#         return 0

# def transcribe_audio_whisper(audio_path, api_key):
#     client = OpenAI(api_key=api_key)
#     with open(audio_path, 'rb') as audio_file:
#         transcript = client.audio.transcriptions.create(
#             model="whisper-1",
#             file=audio_file,
#             response_format="verbose_json",
#             timestamp_granularities=["segment"]
#         )
#     return transcript

# def analyze_for_summary(transcript, api_key, target_duration):
#     client = OpenAI(api_key=api_key)
    
#     segments_text = "\n".join([
#         f"[{seg.start:.2f}s - {seg.end:.2f}s]: {seg.text}"
#         for seg in transcript.segments
#     ])
    
#     prompt = f"""Create a {target_duration}-second video summary.

# TRANSCRIPT:
# {segments_text}

# Select 4-6 key segments totaling ~{target_duration} seconds with:
# - Important content
# - Clear speech
# - Complete sentences

# Return ONLY valid JSON:
# [
#   {{
#     "start_time": 0.5,
#     "end_time": 8.3,
#     "reason": "Key point",
#     "text": "segment text"
#   }}
# ]"""

#     response = client.chat.completions.create(
#         model="gpt-4",
#         messages=[
#             {"role": "system", "content": "You are a video editor. Return ONLY valid JSON."},
#             {"role": "user", "content": prompt}
#         ],
#         temperature=0.2,
#         max_tokens=2000
#     )
    
#     result = response.choices[0].message.content.strip()
#     start_idx = result.find('[')
#     end_idx = result.rfind(']')
    
#     if start_idx != -1 and end_idx != -1:
#         return json.loads(result[start_idx:end_idx+1])
#     return []

# def create_summary_video(input_video, segments, output_path):
#     with tempfile.TemporaryDirectory() as temp_dir:
#         segment_files = []
        
#         for i, seg in enumerate(segments):
#             segment_path = os.path.join(temp_dir, f"seg_{i:03d}.mp4")
#             duration = seg['end_time'] - seg['start_time']
            
#             cmd = [
#                 'ffmpeg', '-ss', str(seg['start_time']),
#                 '-i', input_video,
#                 '-t', str(duration),
#                 '-c:v', 'libx264', '-preset', 'fast',
#                 '-c:a', 'aac',
#                 '-y', '-loglevel', 'error', segment_path
#             ]
#             subprocess.run(cmd, timeout=60)
#             segment_files.append(segment_path)
        
#         concat_file = os.path.join(temp_dir, 'concat.txt')
#         with open(concat_file, 'w', encoding='utf-8') as f:
#             for seg_file in segment_files:
#                 f.write(f"file '{seg_file}'\n")
        
#         cmd = [
#             'ffmpeg', '-f', 'concat', '-safe', '0',
#             '-i', concat_file,
#             '-c', 'copy',
#             '-y', '-loglevel', 'error', output_path
#         ]
#         subprocess.run(cmd, timeout=120)
    
#     return output_path

# def summarize_video_to_30sec(video_path, target_duration=30):
#     """
#     Summarize video to 30 seconds (or specified duration)
#     Returns the summarized video path for further processing
#     """
#     openai_key = os.getenv("OPENAI_API_KEY")
#     if not openai_key:
#         raise RuntimeError("OPENAI_API_KEY not found")
    
#     print(f"🎬 Summarizing video to {target_duration}s...")
    
#     with tempfile.TemporaryDirectory() as temp_dir:
#         video_duration = get_video_duration(video_path)
        
#         if video_duration <= target_duration:
#             print(f"⚠️ Video already {video_duration:.1f}s, no summarization needed")
#             return {
#                 'summary_video_path': video_path,
#                 'original_duration': video_duration,
#                 'summary_duration': video_duration,
#                 'was_summarized': False
#             }
        
#         # Extract and transcribe
#         audio_path = os.path.join(temp_dir, "audio.mp3")
#         extract_audio(video_path, audio_path)
        
#         transcript = transcribe_audio_whisper(audio_path, openai_key)
#         segments = analyze_for_summary(transcript, openai_key, target_duration)
        
#         if not segments:
#             raise ValueError("No segments found for summarization")
        
#         # Create summary in temp directory
#         summary_path = os.path.join(temp_dir, "summary.mp4")
#         create_summary_video(video_path, segments, summary_path)
        
#         # Move to persistent temp location for processing
#         from shared_components import get_output_base_path
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#         final_summary_path = os.path.join(
#             "temp_downloads",
#             f"summarized_{timestamp}.mp4"
#         )
        
#         import shutil
#         shutil.copy2(summary_path, final_summary_path)
        
#         summary_duration = sum(s['end_time'] - s['start_time'] for s in segments)
        
#         print(f"✅ Summarized: {video_duration:.1f}s → {summary_duration:.1f}s")
        
#         return {
#             'summary_video_path': final_summary_path,
#             'original_duration': video_duration,
#             'summary_duration': summary_duration,
#             'was_summarized': True,
#             'segments_count': len(segments)
#         }