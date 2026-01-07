# audio_summarizer.py
import os
import json
from datetime import datetime
from openai import OpenAI
from pydub import AudioSegment
from dotenv import load_dotenv

load_dotenv()

def get_audio_duration(audio_path):
    """Get audio duration in seconds"""
    audio = AudioSegment.from_file(audio_path)
    return len(audio) / 1000.0

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

def analyze_for_audio_summary(transcript, api_key, target_duration):
    client = OpenAI(api_key=api_key)
    
    segments_text = "\n".join([
        f"[{seg.start:.2f}s - {seg.end:.2f}s]: {seg.text}"
        for seg in transcript.segments
    ])
    
    prompt = f"""Create a {target_duration}-second audio summary.

TRANSCRIPT:
{segments_text}

Select 4-6 key segments totaling ~{target_duration} seconds.

Return ONLY valid JSON:
[
  {{
    "start_time": 0.5,
    "end_time": 8.3,
    "text": "segment text"
  }}
]"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an audio editor. Return ONLY valid JSON."},
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

def create_summary_audio(input_audio_path, segments, output_path):
    """Extract and concatenate audio segments"""
    audio = AudioSegment.from_file(input_audio_path)
    summary = AudioSegment.empty()
    
    for seg in segments:
        start_ms = int(seg['start_time'] * 1000)
        end_ms = int(seg['end_time'] * 1000)
        summary += audio[start_ms:end_ms]
    
    summary.export(output_path, format="mp3")
    return output_path

def summarize_audio_to_30sec(audio_path, target_duration=30):
    """
    Summarize audio to 30 seconds (or specified duration)
    Returns the summarized audio path for further processing
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise RuntimeError("OPENAI_API_KEY not found")
    
    print(f"🎵 Summarizing audio to {target_duration}s...")
    
    audio_duration = get_audio_duration(audio_path)
    
    if audio_duration <= target_duration:
        print(f"⚠️ Audio already {audio_duration:.1f}s, no summarization needed")
        return {
            'summary_audio_path': audio_path,
            'original_duration': audio_duration,
            'summary_duration': audio_duration,
            'was_summarized': False
        }
    
    # Transcribe
    transcript = transcribe_audio_whisper(audio_path, openai_key)
    segments = analyze_for_audio_summary(transcript, openai_key, target_duration)
    
    if not segments:
        raise ValueError("No segments found for summarization")
    
    # Create summary
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_path = os.path.join("temp_downloads", f"summarized_{timestamp}.mp3")
    
    create_summary_audio(audio_path, segments, summary_path)
    
    summary_duration = sum(s['end_time'] - s['start_time'] for s in segments)
    
    print(f"✅ Summarized: {audio_duration:.1f}s → {summary_duration:.1f}s")
    
    return {
        'summary_audio_path': summary_path,
        'original_duration': audio_duration,
        'summary_duration': summary_duration,
        'was_summarized': True,
        'segments_count': len(segments)
    }