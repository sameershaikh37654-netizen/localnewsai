
import os
import time
import shutil
import cv2
import numpy as np
import logging
import difflib
import re

# ================= CONFIG =================
WAIT_WINDOW = 600         # 10 minutes
SIMILARITY_THRESHOLD = 0.75
LOCATION_MATCH_THRESHOLD = 0.85
SCAN_INTERVAL = 5          # seconds

BASE_DIR = os.getcwd()
INCOMING_DIR = os.path.join(BASE_DIR, "incoming")
FINAL_DIR = os.path.join(BASE_DIR, "final")
DUPLICATES_DIR = os.path.join(BASE_DIR, "duplicates")

for d in [INCOMING_DIR, FINAL_DIR, DUPLICATES_DIR]:
    os.makedirs(d, exist_ok=True)

# ================= LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ================= INCIDENT STORE =================
incident_store = {}

# ================= LOCATION UTILITIES =================
def normalize_location(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)   # remove dots, commas
    text = re.sub(r"\s+", " ", text).strip()
    return text

def find_matching_incident(uploaded_location: str):
    """
    Compare uploaded location with existing incidents.
    If similarity >= threshold, return matched incident key.
    Else return normalized uploaded location as new key.
    """
    uploaded_norm = normalize_location(uploaded_location)

    best_match = None
    best_score = 0

    for existing in incident_store.keys():
        existing_norm = normalize_location(existing)
        score = difflib.SequenceMatcher(None, uploaded_norm, existing_norm).ratio()

        if score > best_score:
            best_score = score
            best_match = existing

    if best_match and best_score >= LOCATION_MATCH_THRESHOLD:
        logging.info(
            f"Location matched: '{uploaded_location}' → '{best_match}' "
            f"(score={best_score*100:.1f}%)"
        )
        return best_match

    logging.info(
        f"New location created: '{uploaded_location}' "
        f"(best_score={best_score*100:.1f}%)"
    )
    return uploaded_location

# ================= SAFE MOVE =================
def safe_move(src, dst_dir):
    if not os.path.exists(src):
        logging.warning(f"Missing file: {src}")
        return
    dst = os.path.join(dst_dir, os.path.basename(src))
    shutil.move(src, dst)
    logging.info(f"MOVED → {dst}")

# ================= VIDEO UTILITIES =================
def get_video_frames(video_path, max_frames=8):
    cap = cv2.VideoCapture(video_path)
    frames = []
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, total // max_frames)

    i = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if i % step == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (128, 128))
            frames.append(gray)
        i += 1

    cap.release()
    return frames

def frame_similarity(f1, f2):
    f1 = f1.astype(np.float32)
    f2 = f2.astype(np.float32)
    num = np.sum((f1 - f1.mean()) * (f2 - f2.mean()))
    den = np.sqrt(np.sum((f1 - f1.mean())**2) * np.sum((f2 - f2.mean())**2))
    return num / den if den != 0 else 0

def video_similarity(v1, v2):
    f1 = get_video_frames(v1)
    f2 = get_video_frames(v2)
    n = min(len(f1), len(f2))
    if n == 0:
        return 0
    return float(np.mean([frame_similarity(f1[i], f2[i]) for i in range(n)]))

def video_duration(path):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()
    return frames / fps if fps > 0 else 0

def motion_score(path):
    cap = cv2.VideoCapture(path)
    prev = None
    motion = 0
    count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev is not None:
            motion += np.sum(cv2.absdiff(prev, gray))
            count += 1
        prev = gray
    cap.release()
    return motion / max(count, 1)

def pick_best_video(videos):
    scored = [(v, video_duration(v), motion_score(v)) for v in videos]
    scored.sort(key=lambda x: (x[1], x[2]), reverse=True)
    return scored[0][0]

# ================= INCIDENT PROCESSING =================
def process_incident(location):
    incident = incident_store[location]
    items = incident["items"]

    videos = [i["path"] for i in items if i["type"] == "video"]

    logging.info(
        f"Processing incident: {location} | videos:{len(videos)}"
    )

    if videos:
        best = pick_best_video(videos)
        for v in videos:
            safe_move(v, FINAL_DIR if v == best else DUPLICATES_DIR)

    del incident_store[location]
    logging.info(f"Incident completed: {location}")

# ================= MAIN LOOP =================
logging.info("🚀 Incident processor started")

while True:
    now = time.time()

    for filename in os.listdir(INCOMING_DIR):
        path = os.path.join(INCOMING_DIR, filename)
        if not os.path.isfile(path):
            continue

        try:
            _, raw_location, _ = filename.split("_", 2)
        except ValueError:
            logging.warning(f"Invalid filename format: {filename}")
            continue

        location = find_matching_incident(raw_location)

        ext = filename.split(".")[-1].lower()
        ctype = "video" if ext in ["mp4", "m4a"] else "other"

        if location not in incident_store:
            incident_store[location] = {
                "start_time": now,
                "items": []
            }
            logging.info(f"New incident created: {location}")

        if path not in [i["path"] for i in incident_store[location]["items"]]:
            incident_store[location]["items"].append({
                "type": ctype,
                "path": path
            })
            logging.info(f"Registered file: {filename}")

    for loc in list(incident_store.keys()):
        if now - incident_store[loc]["start_time"] >= WAIT_WINDOW:
            process_incident(loc)

    time.sleep(SCAN_INTERVAL)