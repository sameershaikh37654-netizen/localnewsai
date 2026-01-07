"""
NewsBot Main File with Moderation Integration
Flow: Input → Extract Content → Generate Script → MODERATION → TTS (if SAFE)
"""

import os
import json
import requests
import shutil
from pathlib import Path
from flask import Flask, request
from dotenv import load_dotenv
from datetime import datetime
import mimetypes
import time

from openai import OpenAI
from file_manager import FileManager
from shared_components import make_client
from video import process_video
from audio import process_audio
from image import process_image
from video_summarizer import summarize_video_to_30sec
from audio_sumerizer import summarize_audio_to_30sec

# Import moderation analyzers
from text_processor import analyze_text
from vision_processor import analyze_image as moderate_image
from audio_processor import analyze_audio as moderate_audio
from video_processor import analyze_video as moderate_video

load_dotenv()

app = Flask(__name__)

# ===============================
# CONFIG & ENVIRONMENT VARIABLES
# ===============================
GUPSHUP_API_KEY = os.getenv("GUPSHUP_API_KEY")
GUPSHUP_SOURCE_NUMBER = os.getenv("GUPSHUP_SOURCE_NUMBER")
GUPSHUP_APP_NAME = os.getenv("GUPSHUP_APP_NAME", "lastnumber")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

GUPSHUP_SEND_URL = "https://api.gupshup.io/wa/api/v1/msg"

# ===============================
# MODERATION FOLDERS
# ===============================
BASE_MOD_DIR = Path("content_store")
MOD_SAFE_DIR = BASE_MOD_DIR / "safe"
MOD_REVIEW_DIR = BASE_MOD_DIR / "manual_review"
MOD_BLOCK_DIR = BASE_MOD_DIR / "block"

# Create moderation folders
for folder in [MOD_SAFE_DIR, MOD_REVIEW_DIR, MOD_BLOCK_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# ===============================
# FILE MANAGER & TEMP DIRECTORY
# ===============================
file_manager = FileManager()
TEMP_DIR = "temp_downloads"
os.makedirs(TEMP_DIR, exist_ok=True)

# ===============================
# MESSAGE DEDUPLICATION
# ===============================
PROCESSED_MESSAGES = {}
MESSAGE_CACHE_DURATION = 300

# ===============================
# PENDING REVIEWS TRACKING
# ===============================
PENDING_REVIEWS = {}  # {review_id: {sender, file_prefix, media_type, script_text, ...}}


def is_duplicate_message(message_id: str) -> bool:
    """Check if message was already processed"""
    current_time = time.time()
    expired = [mid for mid, ts in PROCESSED_MESSAGES.items() if current_time - ts > MESSAGE_CACHE_DURATION]
    for mid in expired:
        del PROCESSED_MESSAGES[mid]
    
    if message_id in PROCESSED_MESSAGES:
        print(f"⏭️ Duplicate: {message_id[:20]}...")
        return True
    
    PROCESSED_MESSAGES[message_id] = current_time
    return False


# ===============================
# MODERATION FUNCTIONS
# ===============================

def moderate_content(content: str = None, file_path: str = None, media_type: str = "text") -> dict:
    """
    Run moderation on content before TTS
    
    Args:
        content: Text content to moderate (for text/script moderation)
        file_path: Path to media file (for image/audio/video moderation)
        media_type: Type of content ("text", "image", "audio", "video")
    
    Returns:
        {"decision": "SAFE"|"REVIEW"|"BLOCK", "reason": str, "flags": list}
    """
    try:
        print(f"🔍 Running moderation for {media_type}...")
        
        if media_type == "text" and content:
            # Moderate text/script content
            result = analyze_text(content)
        
        elif media_type == "image" and file_path:
            # Moderate image content
            with open(file_path, 'rb') as f:
                result = moderate_image(f)
        
        elif media_type == "audio" and file_path:
            # Moderate audio content
            result = moderate_audio(file_path)
        
        elif media_type == "video" and file_path:
            # Moderate video content
            with open(file_path, 'rb') as f:
                result = moderate_video(f)
        
        else:
            # Default: pass through as safe
            result = {"decision": "SAFE", "reason": "No content to moderate"}
        
        decision = result.get("decision", "SAFE")
        print(f"📋 Moderation result: {decision}")
        
        return result
        
    except Exception as e:
        print(f"⚠️ Moderation error: {e}")
        # On moderation failure, default to REVIEW for safety
        return {
            "decision": "REVIEW",
            "reason": f"Moderation failed: {str(e)}",
            "flags": ["moderation_error"]
        }


def save_for_review(file_prefix: str, media_type: str, script_text: str, 
                    mod_result: dict, sender: str, input_path: str = None) -> str:
    """
    Save content for manual review
    
    Returns:
        review_id: Unique identifier for this review
    """
    review_id = f"{file_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    review_folder = MOD_REVIEW_DIR / review_id
    review_folder.mkdir(exist_ok=True)
    
    # Save script
    with open(review_folder / "script.txt", "w", encoding="utf-8") as f:
        f.write(script_text)
    
    # Save moderation metadata
    review_data = {
        "review_id": review_id,
        "file_prefix": file_prefix,
        "media_type": media_type,
        "sender": sender,
        "timestamp": datetime.now().isoformat(),
        "moderation_result": mod_result,
        "status": "pending"
    }
    
    with open(review_folder / "review.json", "w", encoding="utf-8") as f:
        json.dump(review_data, f, indent=2)
    
    # Copy input file if provided
    if input_path and os.path.exists(input_path):
        ext = os.path.splitext(input_path)[1]
        shutil.copy(input_path, review_folder / f"input{ext}")
    
    # Track pending review
    PENDING_REVIEWS[review_id] = {
        "sender": sender,
        "file_prefix": file_prefix,
        "media_type": media_type,
        "script_text": script_text,
        "review_folder": str(review_folder)
    }
    
    print(f"📝 Saved for review: {review_id}")
    return review_id


def check_review_status(review_id: str) -> dict:
    """
    Check if a review has been approved/rejected
    
    Returns:
        {"status": "pending"|"approved"|"rejected", ...}
    """
    review_folder = MOD_REVIEW_DIR / review_id
    
    if not review_folder.exists():
        # Check if moved to safe or block
        if (MOD_SAFE_DIR / f"{review_id}_script.txt").exists():
            return {"status": "approved"}
        elif (MOD_BLOCK_DIR / f"{review_id}_script.txt").exists():
            return {"status": "rejected"}
        return {"status": "not_found"}
    
    # Check for approve/reject marker files
    if (review_folder / "approve.txt").exists():
        return {"status": "approved"}
    elif (review_folder / "reject.txt").exists():
        return {"status": "rejected"}
    
    return {"status": "pending"}


def process_approved_review(review_id: str) -> str:
    """
    Process an approved review - generate TTS and complete the pipeline
    
    Returns:
        Result message to send to user
    """
    if review_id not in PENDING_REVIEWS:
        return "❌ Review not found in pending reviews"
    
    review_data = PENDING_REVIEWS[review_id]
    review_folder = Path(review_data["review_folder"])
    
    try:
        # Read the script
        script_path = review_folder / "script.txt"
        with open(script_path, "r", encoding="utf-8") as f:
            script_text = f.read()
        
        # Generate TTS
        file_prefix = review_data["file_prefix"]
        media_type = review_data["media_type"]
        
        # TODO: Call your TTS function here
        # For now, we'll just move the script to safe folder
        
        # Move to safe folder
        shutil.copy(script_path, MOD_SAFE_DIR / f"{file_prefix}_script.txt")
        
        # Clean up review folder
        shutil.rmtree(review_folder)
        
        # Remove from pending
        del PENDING_REVIEWS[review_id]
        
        return f"✅ Review approved! Script saved: {file_prefix}_script.txt"
        
    except Exception as e:
        return f"❌ Error processing approved review: {str(e)}"


# ===============================
# LLM CHAT FUNCTION
# ===============================

def llm_chat_reply(user_message: str) -> str:
    """Generate LLM response for general queries"""
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful Telugu news bot assistant."},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=500,
            timeout=20
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"


# ===============================
# MEDIA DURATION HELPER
# ===============================

def get_media_duration(file_path: str, media_type: str) -> float:
    """Get duration of audio/video file in seconds"""
    try:
        if media_type == "video":
            from shared_components import get_video_duration
            return get_video_duration(file_path)
        elif media_type == "audio":
            from pydub import AudioSegment
            audio = AudioSegment.from_file(file_path)
            return len(audio) / 1000.0
        return 0
    except Exception as e:
        print(f"⚠️ Duration check failed: {e}")
        return 0


# ===============================
# MAIN MEDIA PROCESSING PIPELINE
# ===============================

def process_media_file(temp_path: str, media_type: str, sender: str) -> dict:
    """
    MAIN PIPELINE with Moderation Integration:
    
    1. Save input file
    2. Run initial moderation on raw media (optional)
    3. Check duration and summarize if needed
    4. Extract content and generate Telugu script
    5. Run moderation on generated script ← KEY STEP
    6. If SAFE → Generate TTS and save
    7. If REVIEW → Save for manual review
    8. If BLOCK → Reject immediately
    
    Returns:
        {"status": "success"|"review"|"blocked"|"error", "message": str, ...}
    """
    try:
        # =========== STEP 1: Save input file ===========
        input_path, file_prefix = file_manager.save_input_file(temp_path, media_type)
        if not input_path:
            return {"status": "error", "message": "❌ Failed to save input file"}
        
        print(f"📁 Saved input: {input_path}")
        
        # =========== STEP 2: Initial moderation on raw media (optional) ===========
        # You can enable this to moderate the input media before processing
        # initial_mod = moderate_content(file_path=input_path, media_type=media_type)
        # if initial_mod.get("decision") == "BLOCK":
        #     return {"status": "blocked", "message": f"🚫 Content blocked: {initial_mod.get('reason')}"}
        
        processing_path = input_path
        was_summarized = False
        original_duration = 0
        final_duration = 0
        
        # =========== STEP 3: Check duration and summarize if needed ===========
        if media_type in ["video", "audio"]:
            try:
                original_duration = get_media_duration(input_path, media_type)
                print(f"⏱️ Duration: {original_duration:.1f}s")
                
                if original_duration > 40:
                    print(f"📊 Duration > 40s, summarizing...")
                    try:
                        if media_type == "video":
                            summary_result = summarize_video_to_30sec(input_path, target_duration=30)
                            processing_path = summary_result['summary_video_path']
                        elif media_type == "audio":
                            summary_result = summarize_audio_to_30sec(input_path, target_duration=30)
                            processing_path = summary_result['summary_audio_path']
                        
                        was_summarized = True
                        final_duration = summary_result['summary_duration']
                        print(f"✅ Summarized: {original_duration:.1f}s → {final_duration:.1f}s")
                    except Exception as e:
                        print(f"⚠️ Summarization failed: {e}, using original")
                        processing_path = input_path
                        final_duration = original_duration
                else:
                    final_duration = original_duration
                    print(f"✅ Duration OK, no summarization needed")
            except Exception as e:
                print(f"⚠️ Duration check error: {e}")
                final_duration = 30
        
        # =========== STEP 4: Read file data and process ===========
        try:
            with open(processing_path, 'rb') as f:
                file_data = f.read()
        except Exception as e:
            return {"status": "error", "message": f"❌ Failed to read file: {str(e)}"}
        
        file_size_mb = len(file_data) / (1024 * 1024)
        
        try:
            client = make_client(OPENAI_API_KEY)
        except Exception as e:
            return {"status": "error", "message": f"❌ Failed to create OpenAI client: {str(e)}"}
        
        # Determine target duration
        if was_summarized or (media_type in ["video", "audio"] and final_duration > 0):
            target_script_duration = min(int(final_duration) + 2, 32)
        else:
            target_script_duration = 30
        
        print(f"🎯 Target script duration: {target_script_duration}s")
        
        # Setup processing
        voice_settings = {
            'speaker': 'arya',
            'pitch': 0.0,
            'pace': 1.15,
            'loudness': 1.5,
            'sample_rate': 22050
        }
        
        temp_process_dir = os.path.join(TEMP_DIR, f"process_{file_prefix}")
        os.makedirs(temp_process_dir, exist_ok=True)
        
        # Process media (extract content + generate Telugu script)
        # NOTE: We process WITHOUT TTS first, then moderate, then generate TTS
        print(f"🎬 Processing {media_type}...")
        result = None
        
        try:
            if media_type == "image":
                result = process_image(
                    processing_path, file_data, client, "AUTO-DETECT", None, None,
                    temp_process_dir, file_prefix, False, None,  # No TTS yet
                    voice_settings
                )
            elif media_type == "audio":
                result = process_audio(
                    processing_path, file_data, client, "AUTO-DETECT", "auto", None, None,
                    temp_process_dir, file_prefix, False, None,  # No TTS yet
                    voice_settings, target_script_duration
                )
            elif media_type == "video":
                result = process_video(
                    processing_path, file_data, client, "AUTO-DETECT", "auto", None, None,
                    temp_process_dir, file_prefix, False, None,  # No TTS yet
                    voice_settings, target_script_duration
                )
            else:
                return {"status": "error", "message": f"⚠️ Unsupported media type: {media_type}"}
        except Exception as e:
            import traceback
            print(f"❌ Processing error: {traceback.format_exc()}")
            return {"status": "error", "message": f"❌ Processing failed: {str(e)}"}
        
        if not result or result['status'] != 'SUCCESS':
            error_msg = result.get('error', 'Unknown error') if result else 'No result'
            return {"status": "error", "message": f"❌ Processing failed: {error_msg}"}
        
        # =========== STEP 5: Get the generated script ===========
        temp_script_path = os.path.join(temp_process_dir, media_type, f"{file_prefix}_script.txt")
        
        try:
            with open(temp_script_path, 'r', encoding='utf-8') as f:
                script_text = f.read()
        except Exception as e:
            # Try to get script from result
            script_text = result.get('script', result.get('telugu_script', ''))
        
        if not script_text:
            return {"status": "error", "message": "❌ Failed to generate script"}
        
        print(f"📄 Generated script ({len(script_text)} chars)")
        
        # =========== STEP 6: Run MODERATION on generated script ===========
        mod_result = moderate_content(content=script_text, media_type="text")
        decision = mod_result.get("decision", "SAFE")
        
        # =========== STEP 7: Handle moderation decision ===========
        
        if decision == "BLOCK":
            # Move to block folder
            shutil.copy(temp_script_path, MOD_BLOCK_DIR / f"{file_prefix}_script.txt")
            
            # Cleanup
            try:
                shutil.rmtree(temp_process_dir)
            except:
                pass
            
            return {
                "status": "blocked",
                "message": f"🚫 Content blocked: {mod_result.get('reason', 'Policy violation')}",
                "flags": mod_result.get("flags", [])
            }
        
        elif decision == "REVIEW":
            # Save for manual review
            review_id = save_for_review(
                file_prefix=file_prefix,
                media_type=media_type,
                script_text=script_text,
                mod_result=mod_result,
                sender=sender,
                input_path=input_path
            )
            
            # Cleanup temp processing dir
            try:
                shutil.rmtree(temp_process_dir)
            except:
                pass
            
            return {
                "status": "review",
                "message": f"⚠️ Content sent for manual review.\n\n📋 Review ID: {review_id}\n\nYou'll be notified when reviewed.",
                "review_id": review_id,
                "reason": mod_result.get("reason", "Manual review required")
            }
        
        # =========== STEP 8: SAFE - Generate TTS and complete ===========
        print("✅ Content passed moderation - generating TTS...")
        
        # Now generate TTS
        try:
            if SARVAM_API_KEY:
                # Re-process with TTS enabled
                if media_type == "image":
                    result = process_image(
                        processing_path, file_data, client, "AUTO-DETECT", None, None,
                        temp_process_dir, file_prefix, True, SARVAM_API_KEY,
                        voice_settings
                    )
                elif media_type == "audio":
                    result = process_audio(
                        processing_path, file_data, client, "AUTO-DETECT", "auto", None, None,
                        temp_process_dir, file_prefix, True, SARVAM_API_KEY,
                        voice_settings, target_script_duration
                    )
                elif media_type == "video":
                    result = process_video(
                        processing_path, file_data, client, "AUTO-DETECT", "auto", None, None,
                        temp_process_dir, file_prefix, True, SARVAM_API_KEY,
                        voice_settings, target_script_duration
                    )
        except Exception as e:
            print(f"⚠️ TTS generation error: {e}")
        
        # Move outputs
        try:
            temp_script_path = os.path.join(temp_process_dir, media_type, f"{file_prefix}_script.txt")
            temp_audio_path = os.path.join(temp_process_dir, media_type, f"{file_prefix}_audio.mp3") if result.get('audio_file') else None
            
            final_paths = file_manager.move_to_output(temp_script_path, temp_audio_path, file_prefix, media_type)
            
            # Also copy to safe folder for moderation tracking
            if os.path.exists(temp_script_path):
                shutil.copy(temp_script_path, MOD_SAFE_DIR / f"{file_prefix}_script.txt")
        except Exception as e:
            print(f"⚠️ Move output error: {e}")
        
        # Build response
        response = f"""✅ {media_type.upper()} processed!

📁 Output files:
📄 {file_prefix}_script.txt"""
        
        if was_summarized:
            response += f"\n⏱️ {original_duration:.1f}s → {final_duration:.1f}s"
        
        output_audio_path = os.path.join(file_manager.output_dir, media_type, f"{file_prefix}_audio.mp3")
        if os.path.exists(output_audio_path):
            response += f"\n🎙️ {file_prefix}_audio.mp3"
        
        response += f"\n\n📰 Format: {result.get('news_format', 'Unknown')}"
        response += f"\n🎯 Duration: {target_script_duration}s"
        response += f"\n✅ Moderation: PASSED"
        
        # Cleanup
        try:
            shutil.rmtree(temp_process_dir)
        except:
            pass
        
        return {
            "status": "success",
            "message": response,
            "file_prefix": file_prefix
        }
        
    except Exception as e:
        import traceback
        print(f"❌ Fatal error: {traceback.format_exc()}")
        return {"status": "error", "message": f"❌ Error: {str(e)}"}


# ===============================
# DOWNLOAD & SEND FUNCTIONS
# ===============================

def download_media(media_url: str, msg_type: str) -> str:
    """Download media file from Gupshup URL"""
    try:
        print(f"🔽 Downloading {msg_type}...")
        headers = {"apikey": GUPSHUP_API_KEY, "User-Agent": "Mozilla/5.0"}
        response = requests.get(media_url, headers=headers, timeout=30, stream=True)
        response.raise_for_status()
        
        ext = mimetypes.guess_extension(response.headers.get('content-type', '').split(';')[0])
        if not ext:
            ext = {'image': '.jpg', 'video': '.mp4', 'audio': '.mp3', 'voice': '.ogg'}.get(msg_type, '.bin')
        
        filepath = os.path.join(TEMP_DIR, f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{msg_type}{ext}")
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(8192):
                if chunk:
                    f.write(chunk)
        
        print(f"✅ Downloaded: {os.path.getsize(filepath)/(1024*1024):.1f} MB")
        return filepath
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return None


def send_whatsapp_message(destination: str, text: str):
    """Send WhatsApp message via Gupshup"""
    payload = {
        "channel": "whatsapp",
        "source": GUPSHUP_SOURCE_NUMBER,
        "destination": destination,
        "src.name": GUPSHUP_APP_NAME,
        "message": json.dumps({"type": "text", "text": text})
    }
    try:
        r = requests.post(
            GUPSHUP_SEND_URL,
            headers={
                "apikey": GUPSHUP_API_KEY,
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data=payload,
            timeout=15
        )
        print(f"📤 Sent: {r.status_code}")
        return r.status_code
    except Exception as e:
        print(f"❌ Send failed: {e}")
        return None


# ===============================
# WEBHOOK HANDLERS
# ===============================

@app.route("/whatsapp/webhook", methods=["POST", "GET"])
@app.route("/gupshup/webhook", methods=["POST", "GET"])
def webhook():
    """Main webhook handler for Gupshup messages"""
    if request.method == "GET":
        return "OK", 200
    
    try:
        data = request.get_json(force=True)
    except:
        return "OK", 200
    
    print("\n" + "="*50)
    print("📨 INCOMING MESSAGE")
    print("="*50)
    
    if data.get("type") != "message":
        print("⏭️ Not a message, skipping")
        return "OK", 200
    
    payload = data.get("payload", {}) or {}
    sender = payload.get("source") or (payload.get("sender") or {}).get("phone")
    msg_type = payload.get("type")
    message_id = payload.get("id")
    
    if not sender or not msg_type:
        print("⚠️ Missing sender or msg_type")
        return "OK", 200
    
    print(f"👤 From: {sender}")
    print(f"📝 Type: {msg_type}")
    
    # DUPLICATE CHECK
    if message_id and is_duplicate_message(message_id):
        return "OK", 200
    
    if msg_type == "text":
        text = payload.get("payload", {}).get("text", "").strip()
        print(f"💬 Text: {text[:100]}")
        
        # =========== COMMAND HANDLERS ===========
        
        if text.lower() == "/status":
            stats = file_manager.get_stats()
            pending_count = len(PENDING_REVIEWS)
            msg = f"""📊 NewsBot Status

Total Files: {stats['total_files']}
🖼️ Images: {stats['images']}
🎵 Audio: {stats['audio']}
🎬 Videos: {stats['videos']}

📋 Pending Reviews: {pending_count}"""
            send_whatsapp_message(sender, msg)
        
        elif text.lower() == "/reviews":
            # List pending reviews for this sender
            user_reviews = [rid for rid, data in PENDING_REVIEWS.items() if data.get("sender") == sender]
            if user_reviews:
                msg = "📋 Your Pending Reviews:\n\n"
                for rid in user_reviews[:5]:  # Show max 5
                    msg += f"• {rid}\n"
                if len(user_reviews) > 5:
                    msg += f"\n... and {len(user_reviews) - 5} more"
            else:
                msg = "✅ No pending reviews for you."
            send_whatsapp_message(sender, msg)
        
        elif text.lower().startswith("/check "):
            # Check specific review status
            review_id = text[7:].strip()
            status = check_review_status(review_id)
            
            if status["status"] == "approved":
                # Process the approved review
                result = process_approved_review(review_id)
                send_whatsapp_message(sender, result)
            elif status["status"] == "rejected":
                send_whatsapp_message(sender, f"🚫 Review {review_id} was rejected.")
            elif status["status"] == "pending":
                send_whatsapp_message(sender, f"⏳ Review {review_id} is still pending.")
            else:
                send_whatsapp_message(sender, f"❓ Review {review_id} not found.")
        
        elif text.lower() == "/help":
            help_text = """🤖 NewsBot with Moderation

📤 Send: Image, Audio, or Video
🎯 We'll create a 30-second script & TTS

🔍 Content is moderated before TTS:
✅ SAFE → Auto-processed
⚠️ REVIEW → Manual review required
🚫 BLOCK → Rejected

📊 Commands:
/status - File count & pending reviews
/reviews - Your pending reviews
/check <id> - Check review status
/help - This message"""
            send_whatsapp_message(sender, help_text)
        
        else:
            # LLM reply with timeout
            try:
                reply = llm_chat_reply(text)
                send_whatsapp_message(sender, reply)
            except Exception as e:
                send_whatsapp_message(sender, f"⚠️ Error: {str(e)}")
    
    elif msg_type in ["image", "video", "audio", "voice"]:
        media_type = "audio" if msg_type == "voice" else msg_type
        print(f"📎 Media type: {media_type}")
        
        # Send processing notification
        send_whatsapp_message(sender, f"⏳ Processing {media_type}...")
        
        media_url = (payload.get("payload", {}).get("url") or 
                    payload.get("payload", {}).get("mediaUrl") or
                    payload.get("payload", {}).get("fileUrl"))
        
        if media_url:
            print(f"🔗 URL: {media_url[:50]}...")
            temp_path = download_media(media_url, msg_type)
            
            if temp_path:
                try:
                    # Process with moderation
                    result = process_media_file(temp_path, media_type, sender)
                    
                    # Send appropriate response based on status
                    send_whatsapp_message(sender, result["message"])
                    
                    try:
                        os.remove(temp_path)
                        print(f"🧹 Cleaned up temp file")
                    except:
                        pass
                        
                except Exception as e:
                    import traceback
                    print(f"❌ Error: {traceback.format_exc()}")
                    error_msg = str(e)[:100]
                    send_whatsapp_message(sender, f"❌ Error: {error_msg}")
            else:
                send_whatsapp_message(sender, "❌ Download failed")
        else:
            send_whatsapp_message(sender, "⚠️ No URL found")
    
    return "OK", 200


# ===============================
# REVIEW MANAGEMENT ENDPOINTS
# ===============================

@app.route("/review/approve/<review_id>", methods=["POST"])
def approve_review(review_id):
    """Approve a pending review (for admin use)"""
    review_folder = MOD_REVIEW_DIR / review_id
    
    if not review_folder.exists():
        return {"error": "Review not found"}, 404
    
    # Create approve marker
    (review_folder / "approve.txt").touch()
    
    # Process the approval
    if review_id in PENDING_REVIEWS:
        sender = PENDING_REVIEWS[review_id].get("sender")
        result = process_approved_review(review_id)
        
        # Notify sender
        if sender:
            send_whatsapp_message(sender, f"✅ Your content has been approved!\n\n{result}")
    
    return {"status": "approved", "review_id": review_id}, 200


@app.route("/review/reject/<review_id>", methods=["POST"])
def reject_review(review_id):
    """Reject a pending review (for admin use)"""
    review_folder = MOD_REVIEW_DIR / review_id
    
    if not review_folder.exists():
        return {"error": "Review not found"}, 404
    
    # Create reject marker
    (review_folder / "reject.txt").touch()
    
    # Move script to block folder
    script_path = review_folder / "script.txt"
    if script_path.exists():
        shutil.copy(script_path, MOD_BLOCK_DIR / f"{review_id}_script.txt")
    
    # Cleanup
    shutil.rmtree(review_folder)
    
    # Notify sender
    if review_id in PENDING_REVIEWS:
        sender = PENDING_REVIEWS[review_id].get("sender")
        if sender:
            send_whatsapp_message(sender, f"🚫 Your content (Review ID: {review_id}) was rejected.")
        del PENDING_REVIEWS[review_id]
    
    return {"status": "rejected", "review_id": review_id}, 200


@app.route("/review/list", methods=["GET"])
def list_reviews():
    """List all pending reviews (for admin use)"""
    reviews = []
    for review_id, data in PENDING_REVIEWS.items():
        reviews.append({
            "review_id": review_id,
            "sender": data.get("sender"),
            "media_type": data.get("media_type"),
            "file_prefix": data.get("file_prefix")
        })
    
    return {"pending_reviews": reviews, "count": len(reviews)}, 200


# ===============================
# HEALTH CHECK
# ===============================

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "stats": file_manager.get_stats(),
        "cache": len(PROCESSED_MESSAGES),
        "pending_reviews": len(PENDING_REVIEWS),
        "moderation_enabled": True
    }, 200


# ===============================
# BACKGROUND REVIEW CHECKER
# ===============================

def check_manual_reviews():
    """
    Check all manual review folders for approve.txt or reject.txt
    This can be called periodically or triggered by a webhook
    """
    review_folders = [f for f in MOD_REVIEW_DIR.iterdir() if f.is_dir()]
    
    for folder in review_folders:
        review_id = folder.name
        approve_file = folder / "approve.txt"
        reject_file = folder / "reject.txt"
        
        if approve_file.exists():
            print(f"✅ Found approval for {review_id}")
            if review_id in PENDING_REVIEWS:
                sender = PENDING_REVIEWS[review_id].get("sender")
                result = process_approved_review(review_id)
                if sender:
                    send_whatsapp_message(sender, f"✅ Your content has been approved!\n\n{result}")
        
        elif reject_file.exists():
            print(f"🚫 Found rejection for {review_id}")
            # Move to block and cleanup
            script_path = folder / "script.txt"
            if script_path.exists():
                shutil.copy(script_path, MOD_BLOCK_DIR / f"{review_id}_script.txt")
            
            if review_id in PENDING_REVIEWS:
                sender = PENDING_REVIEWS[review_id].get("sender")
                if sender:
                    send_whatsapp_message(sender, f"🚫 Your content (Review ID: {review_id}) was rejected.")
                del PENDING_REVIEWS[review_id]
            
            shutil.rmtree(folder)


# ===============================
# MAIN ENTRY POINT
# ===============================

if __name__ == "__main__":
    stats = file_manager.get_stats()
    print("\n" + "="*70)
    print("🤖 NEWSBOT WITH MODERATION - v3.0")
    print("="*70)
    print(f"📁 Base: {file_manager.base_dir}")
    print(f"📊 Files: {stats['total_files']}")
    print(f"\n🔍 Moderation Folders:")
    print(f"   ✅ Safe: {MOD_SAFE_DIR}")
    print(f"   ⚠️ Review: {MOD_REVIEW_DIR}")
    print(f"   🚫 Block: {MOD_BLOCK_DIR}")
    print(f"\n🎯 Pipeline Flow:")
    print("   1️⃣ Receive media via WhatsApp")
    print("   2️⃣ Check duration & summarize if > 40s")
    print("   3️⃣ Extract content & generate Telugu script")
    print("   4️⃣ 🔍 Run moderation on script")
    print("   5️⃣ SAFE → Generate TTS & save")
    print("   6️⃣ REVIEW → Queue for manual review")
    print("   7️⃣ BLOCK → Reject immediately")
    print(f"\n📡 Admin Endpoints:")
    print("   GET  /review/list - List pending reviews")
    print("   POST /review/approve/<id> - Approve review")
    print("   POST /review/reject/<id> - Reject review")
    print("="*70 + "\n")
    app.run(host="0.0.0.0", port=8000, debug=False)




















# import os
# import json
# import requests
# from flask import Flask, request
# from dotenv import load_dotenv
# from datetime import datetime
# import mimetypes
# import time

# from openai import OpenAI
# from file_manager import FileManager
# from shared_components import make_client
# from video import process_video
# from audio import process_audio
# from image import process_image
# from video_summarizer import summarize_video_to_30sec
# from audio_sumerizer import summarize_audio_to_30sec

# load_dotenv()

# app = Flask(__name__)

# GUPSHUP_API_KEY = os.getenv("GUPSHUP_API_KEY")
# GUPSHUP_SOURCE_NUMBER = os.getenv("GUPSHUP_SOURCE_NUMBER")
# GUPSHUP_APP_NAME = os.getenv("GUPSHUP_APP_NAME", "lastnumber")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

# GUPSHUP_SEND_URL = "https://api.gupshup.io/wa/api/v1/msg"

# file_manager = FileManager()
# TEMP_DIR = "temp_downloads"
# os.makedirs(TEMP_DIR, exist_ok=True)

# # Message deduplication
# PROCESSED_MESSAGES = {}
# MESSAGE_CACHE_DURATION = 300

# def is_duplicate_message(message_id: str) -> bool:
#     """Check if message was already processed"""
#     current_time = time.time()
#     expired = [mid for mid, ts in PROCESSED_MESSAGES.items() if current_time - ts > MESSAGE_CACHE_DURATION]
#     for mid in expired:
#         del PROCESSED_MESSAGES[mid]
    
#     if message_id in PROCESSED_MESSAGES:
#         print(f"⏭️ Duplicate: {message_id[:20]}...")
#         return True
    
#     PROCESSED_MESSAGES[message_id] = current_time
#     return False

# def llm_chat_reply(user_message: str) -> str:
#     """Generate LLM response for general queries"""
#     try:
#         client = OpenAI(api_key=OPENAI_API_KEY)
#         response = client.chat.completions.create(
#             model="gpt-4",
#             messages=[
#                 {"role": "system", "content": "You are a helpful Telugu news bot assistant."},
#                 {"role": "user", "content": user_message}
#             ],
#             temperature=0.7,
#             max_tokens=500,
#             timeout=20  # ✅ ADD TIMEOUT
#         )
#         return response.choices[0].message.content
#     except Exception as e:
#         return f"Error: {str(e)}"

# def get_media_duration(file_path: str, media_type: str) -> float:
#     """Get duration of audio/video file in seconds"""
#     try:
#         if media_type == "video":
#             from shared_components import get_video_duration
#             return get_video_duration(file_path)
#         elif media_type == "audio":
#             from pydub import AudioSegment
#             audio = AudioSegment.from_file(file_path)
#             return len(audio) / 1000.0
#         return 0
#     except Exception as e:
#         print(f"⚠️ Duration check failed: {e}")
#         return 0

# def process_media_file(temp_path: str, media_type: str) -> str:
#     """
#     MAIN PIPELINE with proper error handling and timeouts
#     """
#     try:
#         # Step 1: Save input file
#         input_path, file_prefix = file_manager.save_input_file(temp_path, media_type)
#         if not input_path:
#             return "❌ Failed to save input file"
        
#         processing_path = input_path
#         was_summarized = False
#         original_duration = 0
#         final_duration = 0
        
#         # Step 2: Check duration and summarize if needed
#         if media_type in ["video", "audio"]:
#             try:
#                 original_duration = get_media_duration(input_path, media_type)
#                 print(f"⏱️ Duration: {original_duration:.1f}s")
                
#                 if original_duration > 40:
#                     print(f"📊 Duration > 40s, summarizing...")
#                     try:
#                         if media_type == "video":
#                             summary_result = summarize_video_to_30sec(input_path, target_duration=30)
#                             processing_path = summary_result['summary_video_path']
#                         elif media_type == "audio":
#                             summary_result = summarize_audio_to_30sec(input_path, target_duration=30)
#                             processing_path = summary_result['summary_audio_path']
                        
#                         was_summarized = True
#                         final_duration = summary_result['summary_duration']
#                         print(f"✅ Summarized: {original_duration:.1f}s → {final_duration:.1f}s")
#                     except Exception as e:
#                         print(f"⚠️ Summarization failed: {e}, using original")
#                         processing_path = input_path
#                         final_duration = original_duration
#                 else:
#                     final_duration = original_duration
#                     print(f"✅ Duration OK, no summarization needed")
#             except Exception as e:
#                 print(f"⚠️ Duration check error: {e}")
#                 final_duration = 30  # Fallback
        
#         # Step 3: Read file data
#         try:
#             with open(processing_path, 'rb') as f:
#                 file_data = f.read()
#         except Exception as e:
#             return f"❌ Failed to read file: {str(e)}"
        
#         file_size_mb = len(file_data) / (1024 * 1024)
        
#         try:
#             client = make_client(OPENAI_API_KEY)
#         except Exception as e:
#             return f"❌ Failed to create OpenAI client: {str(e)}"
        
#         # Step 4: Determine target duration
#         if was_summarized or (media_type in ["video", "audio"] and final_duration > 0):
#             target_script_duration = min(int(final_duration) + 2, 32)
#         else:
#             target_script_duration = 30
        
#         print(f"🎯 Target script duration: {target_script_duration}s")
        
#         # Step 5: Setup processing
#         voice_settings = {
#             'speaker': 'arya',
#             'pitch': 0.0,
#             'pace': 1.15,
#             'loudness': 1.5,
#             'sample_rate': 22050
#         }
        
#         temp_process_dir = os.path.join(TEMP_DIR, f"process_{file_prefix}")
#         os.makedirs(temp_process_dir, exist_ok=True)
        
#         # Step 6: Process media with timeout protection
#         print(f"🎬 Processing {media_type}...")
#         result = None
        
#         try:
#             if media_type == "image":
#                 result = process_image(
#                     processing_path, file_data, client, "AUTO-DETECT", None, None,
#                     temp_process_dir, file_prefix, bool(SARVAM_API_KEY), SARVAM_API_KEY, 
#                     voice_settings
#                 )
#             elif media_type == "audio":
#                 result = process_audio(
#                     processing_path, file_data, client, "AUTO-DETECT", "auto", None, None,
#                     temp_process_dir, file_prefix, bool(SARVAM_API_KEY), SARVAM_API_KEY, 
#                     voice_settings, target_script_duration
#                 )
#             elif media_type == "video":
#                 result = process_video(
#                     processing_path, file_data, client, "AUTO-DETECT", "auto", None, None,
#                     temp_process_dir, file_prefix, bool(SARVAM_API_KEY), SARVAM_API_KEY, 
#                     voice_settings, target_script_duration
#                 )
#             else:
#                 return f"⚠️ Unsupported media type: {media_type}"
#         except Exception as e:
#             import traceback
#             print(f"❌ Processing error: {traceback.format_exc()}")
#             return f"❌ Processing failed: {str(e)}"
        
#         if not result or result['status'] != 'SUCCESS':
#             error_msg = result.get('error', 'Unknown error') if result else 'No result'
#             return f"❌ Processing failed: {error_msg}"
        
#         # Step 7: Move outputs
#         try:
#             temp_script_path = os.path.join(temp_process_dir, media_type, f"{file_prefix}_script.txt")
#             temp_audio_path = os.path.join(temp_process_dir, media_type, f"{file_prefix}_audio.mp3") if result.get('audio_file') else None
            
#             final_paths = file_manager.move_to_output(temp_script_path, temp_audio_path, file_prefix, media_type)
#         except Exception as e:
#             print(f"⚠️ Move output error: {e}")
        
#         # Step 8: Build response
#         response = f"""✅ {media_type.upper()} processed!

# 📁 Output files:
# 📄 {file_prefix}_script.txt"""
        
#         if was_summarized:
#             response += f"\n⏱️ {original_duration:.1f}s → {final_duration:.1f}s"
        
#         output_audio_path = os.path.join(file_manager.output_dir, media_type, f"{file_prefix}_audio.mp3")
#         if os.path.exists(output_audio_path):
#             response += f"\n🎙️ {file_prefix}_audio.mp3"
        
#         response += f"\n\n📰 Format: {result.get('news_format', 'Unknown')}"
#         response += f"\n🎯 Duration: {target_script_duration}s"
        
#         # Step 9: Cleanup
#         try:
#             import shutil
#             shutil.rmtree(temp_process_dir)
#         except:
#             pass
        
#         return response
        
#     except Exception as e:
#         import traceback
#         print(f"❌ Fatal error: {traceback.format_exc()}")
#         return f"❌ Error: {str(e)}"

# def download_media(media_url: str, msg_type: str) -> str:
#     """Download media file from Gupshup URL"""
#     try:
#         print(f"🔽 Downloading {msg_type}...")
#         headers = {"apikey": GUPSHUP_API_KEY, "User-Agent": "Mozilla/5.0"}
#         response = requests.get(media_url, headers=headers, timeout=30, stream=True)
#         response.raise_for_status()
        
#         ext = mimetypes.guess_extension(response.headers.get('content-type', '').split(';')[0])
#         if not ext:
#             ext = {'.image': '.jpg', 'video': '.mp4', 'audio': '.mp3', 'voice': '.ogg'}.get(msg_type, '.bin')
        
#         filepath = os.path.join(TEMP_DIR, f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{msg_type}{ext}")
        
#         with open(filepath, 'wb') as f:
#             for chunk in response.iter_content(8192):
#                 if chunk:
#                     f.write(chunk)
        
#         print(f"✅ Downloaded: {os.path.getsize(filepath)/(1024*1024):.1f} MB")
#         return filepath
#     except Exception as e:
#         print(f"❌ Download failed: {e}")
#         return None

# def send_whatsapp_message(destination: str, text: str):
#     """Send WhatsApp message via Gupshup"""
#     payload = {
#         "channel": "whatsapp",
#         "source": GUPSHUP_SOURCE_NUMBER,
#         "destination": destination,
#         "src.name": GUPSHUP_APP_NAME,
#         "message": json.dumps({"type": "text", "text": text})
#     }
#     try:
#         r = requests.post(
#             GUPSHUP_SEND_URL,
#             headers={
#                 "apikey": GUPSHUP_API_KEY,
#                 "Content-Type": "application/x-www-form-urlencoded"
#             },
#             data=payload,
#             timeout=15
#         )
#         print(f"📤 Sent: {r.status_code}")
#         return r.status_code
#     except Exception as e:
#         print(f"❌ Send failed: {e}")
#         return None

# @app.route("/whatsapp/webhook", methods=["POST", "GET"])
# @app.route("/gupshup/webhook", methods=["POST", "GET"])
# def webhook():
#     """Main webhook handler for Gupshup messages"""
#     if request.method == "GET":
#         return "OK", 200
    
#     try:
#         data = request.get_json(force=True)
#     except:
#         return "OK", 200
    
#     print("\n" + "="*50)
#     print("📨 INCOMING MESSAGE")
#     print("="*50)
    
#     if data.get("type") != "message":
#         print("⏭️ Not a message, skipping")
#         return "OK", 200
    
#     payload = data.get("payload", {}) or {}
#     sender = payload.get("source") or (payload.get("sender") or {}).get("phone")
#     msg_type = payload.get("type")
#     message_id = payload.get("id")
    
#     if not sender or not msg_type:
#         print("⚠️ Missing sender or msg_type")
#         return "OK", 200
    
#     print(f"👤 From: {sender}")
#     print(f"📝 Type: {msg_type}")
    
#     # DUPLICATE CHECK
#     if message_id and is_duplicate_message(message_id):
#         return "OK", 200
    
#     if msg_type == "text":
#         text = payload.get("payload", {}).get("text", "").strip()
#         print(f"💬 Text: {text[:100]}")
        
#         if text.lower() == "/status":
#             stats = file_manager.get_stats()
#             msg = f"""📊 NewsBot Status

# Total Files: {stats['total_files']}
# 🖼️ Images: {stats['images']}
# 🎵 Audio: {stats['audio']}
# 🎬 Videos: {stats['videos']}"""
#             send_whatsapp_message(sender, msg)
            
#         elif text.lower() == "/help":
#             help_text = """🤖 NewsBot

# 📤 Send: Image, Audio, or Video
# 🎯 We'll create a 30-second script & TTS

# 📊 Commands:
# /status - File count
# /help - This message"""
#             send_whatsapp_message(sender, help_text)
            
#         else:
#             # LLM reply with timeout
#             try:
#                 reply = llm_chat_reply(text)
#                 send_whatsapp_message(sender, reply)
#             except Exception as e:
#                 send_whatsapp_message(sender, f"⚠️ Error: {str(e)}")
    
#     elif msg_type in ["image", "video", "audio", "voice"]:
#         media_type = "audio" if msg_type == "voice" else msg_type
#         print(f"📎 Media type: {media_type}")
        
#         # Send processing notification
#         send_whatsapp_message(sender, f"⏳ Processing {media_type}...")
        
#         media_url = (payload.get("payload", {}).get("url") or 
#                     payload.get("payload", {}).get("mediaUrl") or
#                     payload.get("payload", {}).get("fileUrl"))
        
#         if media_url:
#             print(f"🔗 URL: {media_url[:50]}...")
#             temp_path = download_media(media_url, msg_type)
            
#             if temp_path:
#                 try:
#                     result = process_media_file(temp_path, media_type)
#                     print(f"✅ Processing complete, sending result...")
#                     send_whatsapp_message(sender, result)
                    
#                     try:
#                         os.remove(temp_path)
#                         print(f"🧹 Cleaned up temp file")
#                     except:
#                         pass
                        
#                 except Exception as e:
#                     import traceback
#                     print(f"❌ Error: {traceback.format_exc()}")
#                     error_msg = str(e)[:100]
#                     send_whatsapp_message(sender, f"❌ Error: {error_msg}")
#             else:
#                 send_whatsapp_message(sender, "❌ Download failed")
#         else:
#             send_whatsapp_message(sender, "⚠️ No URL found")
    
#     return "OK", 200

# @app.route("/health", methods=["GET"])
# def health():
#     """Health check endpoint"""
#     return {
#         "status": "ok",
#         "stats": file_manager.get_stats(),
#         "cache": len(PROCESSED_MESSAGES)
#     }, 200

# if __name__ == "__main__":
#     stats = file_manager.get_stats()
#     print("\n" + "="*70)
#     print("🤖 NEWSBOT - FIXED VERSION")
#     print("="*70)
#     print(f"📁 Base: {file_manager.base_dir}")
#     print(f"📊 Files: {stats['total_files']}")
#     print("="*70 + "\n")
#     app.run(host="0.0.0.0", port=8000, debug=False)  # ✅ debug=False to prevent hangs