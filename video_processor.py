

import tempfile
from moviepy.editor import VideoFileClip
from vision_processor import analyze_image
from audio_processor import analyze_audio


def extract_frames(clip, interval=0.5, max_frames=10):
    frames = []
    t = 0
    while t < clip.duration and len(frames) < max_frames:
        frames.append(clip.get_frame(t))
        t += interval
    return frames


def analyze_video(video_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
        f.write(video_file.read())
        path = f.name

    clip = VideoFileClip(path)
    frames = extract_frames(clip)

    ai_flags = []

    for frame in frames:
        result = analyze_image(frame)
        if result["decision"] == "REVIEW":
            ai_flags.append(True)

    audio_result = analyze_audio(video_file)
    audio_ai = audio_result["decision"] == "REVIEW"

    suspected_ai = (len(ai_flags) / max(len(frames), 1)) >= 0.4 or audio_ai

    if suspected_ai:
        return {
            "summary": "Possible AI-generated or manipulated video detected. Manual editorial review is required.",
            "decision": "REVIEW",
            "review_reasons": ["suspected_ai_generated_or_manipulated"]
        }

    return {
        "summary": "No strong indicators of AI-generated or manipulated content detected.",
        "decision": "SAFE",
        "review_reasons": []
    }