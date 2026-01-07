import os
import shutil
import json
import time
from pathlib import Path

from text_processor import analyze_text
from vision_processor import analyze_image
from audio_processor import analyze_audio
from video_processor import analyze_video

# ===============================
# CONFIG & FOLDERS
# ===============================
INPUT_FOLDER = Path("inputs")
BASE_DIR = Path("content_store")
SAFE_DIR = BASE_DIR / "safe"
REVIEW_DIR = BASE_DIR / "manual_review"
BLOCK_DIR = BASE_DIR / "block"

POLL_INTERVAL = 5  # seconds

# Supported file types
TEXT_EXT = [".txt"]
IMAGE_EXT = [".jpg", ".jpeg", ".png"]
AUDIO_EXT = [".mp3", ".wav", ".m4a"]
VIDEO_EXT = [".mp4", ".mov", ".avi"]

# Create folders automatically
for folder in [INPUT_FOLDER, SAFE_DIR, REVIEW_DIR, BLOCK_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

print("📰 Editorial Moderation Pipeline started.")
print("Watching folder:", INPUT_FOLDER.resolve())
print("Drop files (.txt, .jpg/.png, .mp3/.wav/.m4a, .mp4/.mov/.avi) here to process.")

# ===============================
# HELPER FUNCTIONS
# ===============================

def move_file(src, dst_dir):
    dst = dst_dir / src.name
    shutil.move(str(src), str(dst))
    return dst

def save_review_metadata(folder, result):
    with open(folder / "review.json", "w") as f:
        json.dump(result, f, indent=2)

def process_file(file_path):
    file_path = Path(file_path)
    ext = file_path.suffix.lower()

    try:
        # Detect type and analyze
        if ext in TEXT_EXT:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            result = analyze_text(text)

        elif ext in IMAGE_EXT:
            with open(file_path, "rb") as f:
                result = analyze_image(f)

        elif ext in AUDIO_EXT:
            result = analyze_audio(str(file_path))

        elif ext in VIDEO_EXT:
            with open(file_path, "rb") as f:
                result = analyze_video(f)

        else:
            print(f"❌ Unsupported file type: {file_path.name}")
            return

        decision = result.get("decision")

        # ---------- SAFE ----------
        if decision == "SAFE":
            move_file(file_path, SAFE_DIR)
            print(f"✅ {file_path.name} auto-approved → SAFE")

        # ---------- BLOCK ----------
        elif decision == "BLOCK":
            move_file(file_path, BLOCK_DIR)
            print(f"🚫 {file_path.name} BLOCKED → BLOCK")

        # ---------- REVIEW ----------
        elif decision == "REVIEW":
            review_folder = REVIEW_DIR / file_path.stem
            review_folder.mkdir(exist_ok=True)
            moved_file = move_file(file_path, review_folder)
            save_review_metadata(review_folder, result)
            print(f"⚠️ {file_path.name} moved to MANUAL_REVIEW → review.json created")
            print("To approve: add 'approve.txt' inside folder")
            print("To reject: add 'reject.txt' inside folder")

        else:
            print(f"⚠️ Unknown decision for {file_path.name}")

    except Exception as e:
        print(f"❌ Error processing {file_path.name}: {e}")

def check_manual_reviews():
    """
    Check all manual review folders for approve.txt or reject.txt
    """
    review_folders = [f for f in REVIEW_DIR.iterdir() if f.is_dir()]
    for folder in review_folders:
        approve_file = folder / "approve.txt"
        reject_file = folder / "reject.txt"

        # There should be exactly one content file per folder
        content_files = [f for f in folder.iterdir() if f.is_file() and f.suffix != ".txt"]
        if not content_files:
            continue
        content_file = content_files[0]

        if approve_file.exists():
            shutil.move(str(content_file), SAFE_DIR / content_file.name)
            shutil.rmtree(folder)
            print(f"✅ {content_file.name} approved via approve.txt → SAFE")

        elif reject_file.exists():
            shutil.move(str(content_file), BLOCK_DIR / content_file.name)
            shutil.rmtree(folder)
            print(f"🚫 {content_file.name} rejected via reject.txt → BLOCK")

# ===============================
# FOLDER WATCH LOOP
# ===============================
processed_files = set()

while True:
    try:
        # Check new files in inputs/
        files = [f for f in INPUT_FOLDER.iterdir() if f.is_file()]
        for f in files:
            if f in processed_files:
                continue
            print(f"\n🔹 Processing new file: {f.name}")
            process_file(f)
            processed_files.add(f)

        # Check manual review folders for approve/reject marker files
        check_manual_reviews()

        time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\n🛑 Pipeline stopped by user")
        break
    except Exception as e:
        print(f"❌ Error in folder watcher: {e}")
        time.sleep(POLL_INTERVAL)