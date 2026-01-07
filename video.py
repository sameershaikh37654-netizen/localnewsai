# import os
# from datetime import datetime
# import streamlit as st

# from shared_components import (
#     save_upload_to_temp, extract_audio_from_video, transcribe_audio,
#     deep_analyze_video, auto_detect_news_type, get_optimal_model,
#     generate_tv_news_script_multilingual, log_to_csv,
#     generate_audio_from_script, VOICE_PRESETS
# )


# def process_video(video_file, client, manual_command, lang_hint, town, incident_time,
#                  session_folder=None, file_prefix="v1",
#                  generate_audio=False, sarvam_api_key=None, voice_settings=None):
    
#     file_size_mb = video_file.size / (1024 * 1024)
#     progress = st.progress(0)
#     status = st.empty()
    
#     try:
#         status.text("🔄 Extracting audio...")
#         progress.progress(20)
        
#         video_path = save_upload_to_temp(video_file)
#         wav_path = os.path.join("temp", f"audio_{int(datetime.now().timestamp())}.wav")
#         os.makedirs("temp", exist_ok=True)
        
#         has_audio = True
#         try:
#             extract_audio_from_video(video_path, wav_path)
#         except RuntimeError as e:
#             if "no audio stream" in str(e).lower():
#                 st.warning("⚠️ Video has no audio - will use only visual analysis")
#                 has_audio = False
#                 transcript = ""
#             else:
#                 raise
        
#         progress.progress(40)
        
#         if has_audio:
#             status.text("🎤 Transcribing...")
#             lang = None if lang_hint == "auto" else lang_hint
#             try:
#                 transcript = transcribe_audio(client, wav_path, lang)
#                 st.success("✓ Transcribed")
#             except Exception as e:
#                 st.warning(f"⚠️ Transcription failed: {str(e)} - Using visual analysis only")
#                 transcript = ""
#         else:
#             transcript = ""
        
#         progress.progress(60)
        
#         status.text("📸 Analyzing video...")
#         content_analysis = deep_analyze_video(client, video_path)
#         st.success("✓ Analyzed")
        
#         with st.expander("📋 Analysis"):
#             col1, col2 = st.columns(2)
#             with col1:
#                 st.text_area("Visual:", content_analysis, height=150, key=f"visual_{file_prefix}")
#             with col2:
#                 st.text_area("Audio:", transcript, height=150, key=f"audio_{file_prefix}")
        
#         progress.progress(70)
        
#         if manual_command == "AUTO-DETECT":
#             status.text("🤖 Detecting news type...")
#             combined = f"VISUAL:\n{content_analysis}\n\nAUDIO:\n{transcript}"
#             selected_commands = auto_detect_news_type(combined, client)
#             st.info(f"Detected: {selected_commands[0]}")
#         else:
#             selected_commands = [manual_command]
        
#         progress.progress(80)
        
#         status.text("📺 Creating Telugu script...")
#         model = get_optimal_model("video", selected_commands, file_size_mb)
        
#         scripts = generate_tv_news_script_multilingual(
#             client=client, model=model,
#             source_type="video",
#             command_types=selected_commands,
#             languages=["te"],
#             transcript=transcript,
#             content_analysis=content_analysis,
#             town=town or None,
#             incident_time=incident_time or None
#         )
        
#         progress.progress(90)
        
#         status.text("💾 Saving script...")
        
#         if session_folder:
#             video_folder = os.path.join(session_folder, "video")
#             os.makedirs(video_folder, exist_ok=True)
            
#             output_filename = f"{file_prefix}_script.txt"
#             output_path = os.path.join(video_folder, output_filename)
            
#             with open(output_path, "w", encoding="utf-8") as f:
#                 f.write(scripts["te"])
#         else:
#             from shared_components import save_tv_script_output_multilingual
#             script_paths = save_tv_script_output_multilingual(scripts, "video", selected_commands)
#             output_path = script_paths["te"]
        
#         audio_path = None
#         if generate_audio and sarvam_api_key:
#             try:
#                 status.text("🎙️ Generating audio...")
#                 progress.progress(95)
                
#                 voice_settings = voice_settings or {}
#                 speaker = voice_settings.get('speaker', 'arya')
#                 pitch = voice_settings.get('pitch', 0.0)
#                 pace = voice_settings.get('pace', 1.0)
#                 loudness = voice_settings.get('loudness', 1.0)
#                 sample_rate = voice_settings.get('sample_rate', 22050)
                
#                 if session_folder:
#                     audio_filename = f"{file_prefix}_audio.mp3"
#                     audio_path = os.path.join(video_folder, audio_filename)
#                 else:
#                     audio_path = None
                
#                 audio_path = generate_audio_from_script(
#                     script_text=scripts["te"],
#                     sarvam_api_key=sarvam_api_key,
#                     speaker=speaker,
#                     pitch=pitch,
#                     pace=pace,
#                     loudness=loudness,
#                     sample_rate=sample_rate,
#                     output_path=audio_path
#                 )
                
#                 st.success(f"✅ Audio generated with {VOICE_PRESETS[speaker]['name']} voice!")
                
#             except Exception as e:
#                 st.warning(f"⚠️ Audio generation failed: {str(e)}")
#                 audio_path = None
        
#         progress.progress(100)
#         status.text("✅ Complete!")
        
#         st.markdown("**📺 Generated Telugu Script:**")
#         st.markdown(f"""
#         <div style="font-family: 'Nirmala UI', 'Gautami', sans-serif; font-size: 16px;
#                     background-color: #f8f9fa; padding: 15px; border-radius: 8px;">
#         {scripts["te"]}
#         </div>
#         """, unsafe_allow_html=True)
        
#         col1, col2 = st.columns(2)
        
#         with col1:
#             with open(output_path, "rb") as f:
#                 st.download_button(
#                     "📥 Download Script (TXT)",
#                     data=f,
#                     file_name=os.path.basename(output_path),
#                     mime="text/plain",
#                     key=f"download_txt_{file_prefix}"
#                 )
        
#         if audio_path and os.path.exists(audio_path):
#             with col2:
#                 with open(audio_path, "rb") as f:
#                     st.download_button(
#                         "📥 Download Audio (MP3)",
#                         data=f,
#                         file_name=os.path.basename(audio_path),
#                         mime="audio/mp3",
#                         key=f"download_audio_{file_prefix}"
#                     )
            
#             st.markdown("### 🔊 Listen to Generated Audio")
#             with open(audio_path, "rb") as f:
#                 st.audio(f.read(), format="audio/mp3")
        
#         output_files = [output_path]
#         if audio_path:
#             output_files.append(audio_path)
        
#         log_to_csv(
#             source_type="VIDEO",
#             input_file_name=video_file.name,
#             input_file_size_mb=file_size_mb,
#             languages=["te"],
#             news_format=selected_commands[0],
#             location=town,
#             incident_time=incident_time,
#             ai_model=model,
#             output_files=output_files,
#             audio_generated=audio_path is not None,
#             status="SUCCESS",
#             notes=f"Prefix: {file_prefix}, Lang: {lang_hint}"
#         )
        
#         return {
#             'status': 'SUCCESS',
#             'output_file': output_path,
#             'audio_file': audio_path,
#             'news_format': selected_commands[0],
#             'model': model
#         }
        
#     except Exception as e:
#         status.text("❌ Failed")
#         st.error(f"Error: {str(e)}")
        
#         log_to_csv(
#             source_type="VIDEO",
#             input_file_name=video_file.name,
#             input_file_size_mb=file_size_mb,
#             languages=["te"],
#             news_format="ERROR",
#             location=town,
#             incident_time=incident_time,
#             ai_model="N/A",
#             output_files=[],
#             audio_generated=False,
#             status="FAILED",
#             notes=f"Error: {str(e)}"
#         )
        
#         return {
#             'status': 'FAILED',
#             'error': str(e)
#         }






# video.py
import os
from datetime import datetime

from shared_components import (
    save_upload_to_temp, extract_audio_from_video, transcribe_audio,
    deep_analyze_video, auto_detect_news_type, get_optimal_model,
    generate_tv_news_script_multilingual, log_to_csv,
    generate_audio_from_script, VOICE_PRESETS
)


# def process_video(video_file_path, video_data, client, manual_command, lang_hint, town, incident_time,
#                  session_folder=None, file_prefix="v1",
#                  generate_audio=False, sarvam_api_key=None, voice_settings=None):
    
#     file_size_mb = len(video_data) / (1024 * 1024)
    
#     try:
#         print("🔄 Extracting audio...")
        
#         video_path = save_upload_to_temp(video_file_path, video_data)
#         wav_path = os.path.join("temp", f"audio_{int(datetime.now().timestamp())}.wav")
#         os.makedirs("temp", exist_ok=True)
        
#         has_audio = True
#         try:
#             extract_audio_from_video(video_path, wav_path)
#         except RuntimeError as e:
#             if "no audio stream" in str(e).lower():
#                 print("⚠️ Video has no audio - will use only visual analysis")
#                 has_audio = False
#                 transcript = ""
#             else:
#                 raise
        
#         if has_audio:
#             print("🎤 Transcribing...")
#             lang = None if lang_hint == "auto" else lang_hint
#             try:
#                 transcript = transcribe_audio(client, wav_path, lang)
#                 print("✓ Transcribed")
#             except Exception as e:
#                 print(f"⚠️ Transcription failed: {str(e)} - Using visual analysis only")
#                 transcript = ""
#         else:
#             transcript = ""
        
#         print("📸 Analyzing video...")
#         content_analysis = deep_analyze_video(client, video_path)
#         print("✓ Analyzed")
        
#         print(f"\n📋 Visual Analysis:\n{content_analysis}\n")
#         if transcript:
#             print(f"📋 Audio Transcript:\n{transcript}\n")
        
#         if manual_command == "AUTO-DETECT":
#             print("🤖 Detecting news type...")
#             combined = f"VISUAL:\n{content_analysis}\n\nAUDIO:\n{transcript}"
#             selected_commands = auto_detect_news_type(combined, client)
#             print(f"Detected: {selected_commands[0]}")
#         else:
#             selected_commands = [manual_command]
        
#         print("📺 Creating Telugu script...")
#         model = get_optimal_model("video", selected_commands, file_size_mb)
        
#         scripts = generate_tv_news_script_multilingual(
#             client=client, model=model,
#             source_type="video",
#             command_types=selected_commands,
#             languages=["te"],
#             transcript=transcript,
#             content_analysis=content_analysis,
#             town=town or None,
#             incident_time=incident_time or None
#         )
        
#         print("💾 Saving script...")
        
#         if session_folder:
#             video_folder = os.path.join(session_folder, "video")
#             os.makedirs(video_folder, exist_ok=True)
            
#             output_filename = f"{file_prefix}_script.txt"
#             output_path = os.path.join(video_folder, output_filename)
            
#             with open(output_path, "w", encoding="utf-8") as f:
#                 f.write(scripts["te"])
#         else:
#             from shared_components import save_tv_script_output_multilingual
#             script_paths = save_tv_script_output_multilingual(scripts, "video", selected_commands)
#             output_path = script_paths["te"]
        
#         audio_path = None
#         if generate_audio and sarvam_api_key:
#             try:
#                 print("🎙️ Generating audio...")
                
#                 voice_settings = voice_settings or {}
#                 speaker = voice_settings.get('speaker', 'arya')
#                 pitch = voice_settings.get('pitch', 0.0)
#                 pace = voice_settings.get('pace', 1.0)
#                 loudness = voice_settings.get('loudness', 1.0)
#                 sample_rate = voice_settings.get('sample_rate', 22050)
                
#                 if session_folder:
#                     audio_filename = f"{file_prefix}_audio.mp3"
#                     audio_path = os.path.join(video_folder, audio_filename)
#                 else:
#                     audio_path = None
                
#                 audio_path = generate_audio_from_script(
#                     script_text=scripts["te"],
#                     sarvam_api_key=sarvam_api_key,
#                     speaker=speaker,
#                     pitch=pitch,
#                     pace=pace,
#                     loudness=loudness,
#                     sample_rate=sample_rate,
#                     output_path=audio_path
#                 )
                
#                 print(f"✅ Audio generated with {VOICE_PRESETS[speaker]['name']} voice!")
                
#             except Exception as e:
#                 print(f"⚠️ Audio generation failed: {str(e)}")
#                 audio_path = None
        
#         print("✅ Complete!")
        
#         print("\n📺 Generated Telugu Script:")
#         print(scripts["te"])
#         print(f"\n📄 Script saved: {output_path}")
        
#         if audio_path:
#             print(f"🔊 Audio saved: {audio_path}")
        
#         output_files = [output_path]
#         if audio_path:
#             output_files.append(audio_path)
        
#         log_to_csv(
#             source_type="VIDEO",
#             input_file_name=os.path.basename(video_file_path),
#             input_file_size_mb=file_size_mb,
#             languages=["te"],
#             news_format=selected_commands[0],
#             location=town,
#             incident_time=incident_time,
#             ai_model=model,
#             output_files=output_files,
#             audio_generated=audio_path is not None,
#             status="SUCCESS",
#             notes=f"Prefix: {file_prefix}, Lang: {lang_hint}"
#         )
        
#         return {
#             'status': 'SUCCESS',
#             'output_file': output_path,
#             'audio_file': audio_path,
#             'news_format': selected_commands[0],
#             'model': model
#         }
        
#     except Exception as e:
#         print(f"❌ Failed: {str(e)}")
        
#         log_to_csv(
#             source_type="VIDEO",
#             input_file_name=os.path.basename(video_file_path),
#             input_file_size_mb=file_size_mb,
#             languages=["te"],
#             news_format="ERROR",
#             location=town,
#             incident_time=incident_time,
#             ai_model="N/A",
#             output_files=[],
#             audio_generated=False,
#             status="FAILED",
#             notes=f"Error: {str(e)}"
#         )
        
#         return {
#             'status': 'FAILED',
#             'error': str(e)
#         }

def process_video(video_file_path, video_data, client, manual_command, lang_hint, town, incident_time,
                 session_folder=None, file_prefix="v1",
                 generate_audio=False, sarvam_api_key=None, voice_settings=None,
                 target_script_duration=30):  # NEW PARAMETER
    
    file_size_mb = len(video_data) / (1024 * 1024)
    
    try:
        print("🔄 Extracting audio...")
        
        video_path = save_upload_to_temp(video_file_path, video_data)
        wav_path = os.path.join("temp", f"audio_{int(datetime.now().timestamp())}.wav")
        os.makedirs("temp", exist_ok=True)
        
        has_audio = True
        try:
            extract_audio_from_video(video_path, wav_path)
        except RuntimeError as e:
            if "no audio stream" in str(e).lower():
                print("⚠️ Video has no audio - will use only visual analysis")
                has_audio = False
                transcript = ""
            else:
                raise
        
        if has_audio:
            print("🎤 Transcribing...")
            lang = None if lang_hint == "auto" else lang_hint
            try:
                transcript = transcribe_audio(client, wav_path, lang)
                print("✓ Transcribed")
            except Exception as e:
                print(f"⚠️ Transcription failed: {str(e)} - Using visual analysis only")
                transcript = ""
        else:
            transcript = ""
        
        print("📸 Analyzing video...")
        content_analysis = deep_analyze_video(client, video_path)
        print("✓ Analyzed")
        
        print(f"\n📋 Visual Analysis:\n{content_analysis[:300]}...\n")
        if transcript:
            print(f"📋 Audio Transcript:\n{transcript[:300]}...\n")
        
        if manual_command == "AUTO-DETECT":
            print("🤖 Detecting news type...")
            combined = f"VISUAL:\n{content_analysis}\n\nAUDIO:\n{transcript}"
            selected_commands = auto_detect_news_type(combined, client)
            print(f"Detected: {selected_commands[0]}")
        else:
            selected_commands = [manual_command]
        
        print(f"📺 Creating {target_script_duration}s Telugu script...")
        model = get_optimal_model("video", selected_commands, file_size_mb)
        
        # Use duration-aware script generation
        from shared_components import generate_tv_news_script_multilingual_with_duration
        
        scripts = generate_tv_news_script_multilingual_with_duration(
            client=client, model=model,
            source_type="video",
            command_types=selected_commands,
            languages=["te"],
            target_duration_seconds=target_script_duration,  # Pass duration constraint
            transcript=transcript[:1000] if transcript else None,  # Limit transcript length
            content_analysis=content_analysis[:1000],  # Limit analysis length
            town=town or None,
            incident_time=incident_time or None
        )
        
        print("💾 Saving script...")
        
        if session_folder:
            video_folder = os.path.join(session_folder, "video")
            os.makedirs(video_folder, exist_ok=True)
            
            output_filename = f"{file_prefix}_script.txt"
            output_path = os.path.join(video_folder, output_filename)
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(scripts["te"])
        else:
            from shared_components import save_tv_script_output_multilingual
            script_paths = save_tv_script_output_multilingual(scripts, "video", selected_commands)
            output_path = script_paths["te"]
        
        audio_path = None
        if generate_audio and sarvam_api_key:
            try:
                print("🎙️ Generating audio...")
                
                voice_settings = voice_settings or {}
                speaker = voice_settings.get('speaker', 'arya')
                pitch = voice_settings.get('pitch', 0.0)
                pace = voice_settings.get('pace', 1.15)  # Slightly faster pace
                loudness = voice_settings.get('loudness', 1.0)
                sample_rate = voice_settings.get('sample_rate', 22050)
                
                if session_folder:
                    audio_filename = f"{file_prefix}_audio.mp3"
                    audio_path = os.path.join(video_folder, audio_filename)
                else:
                    audio_path = None
                
                audio_path = generate_audio_from_script(
                    script_text=scripts["te"],
                    sarvam_api_key=sarvam_api_key,
                    speaker=speaker,
                    pitch=pitch,
                    pace=pace,
                    loudness=loudness,
                    sample_rate=sample_rate,
                    output_path=audio_path
                )
                
                # Check TTS duration
                from pydub import AudioSegment
                tts_audio = AudioSegment.from_mp3(audio_path)
                tts_duration = len(tts_audio) / 1000.0
                print(f"✅ Audio generated: {tts_duration:.1f}s with {VOICE_PRESETS[speaker]['name']} voice!")
                
                if tts_duration > target_script_duration + 5:
                    print(f"⚠️ Warning: TTS is {tts_duration:.1f}s (target was {target_script_duration}s)")
                
            except Exception as e:
                print(f"⚠️ Audio generation failed: {str(e)}")
                audio_path = None
        
        print("✅ Complete!")
        
        print(f"\n📺 Generated Telugu Script ({target_script_duration}s target):")
        print(scripts["te"])
        print(f"\n📄 Script saved: {output_path}")
        
        if audio_path:
            print(f"🔊 Audio saved: {audio_path}")
        
        output_files = [output_path]
        if audio_path:
            output_files.append(audio_path)
        
        log_to_csv(
            source_type="VIDEO",
            input_file_name=os.path.basename(video_file_path),
            input_file_size_mb=file_size_mb,
            languages=["te"],
            news_format=selected_commands[0],
            location=town,
            incident_time=incident_time,
            ai_model=model,
            output_files=output_files,
            audio_generated=audio_path is not None,
            status="SUCCESS",
            notes=f"Prefix: {file_prefix}, Target: {target_script_duration}s"
        )
        
        return {
            'status': 'SUCCESS',
            'output_file': output_path,
            'audio_file': audio_path,
            'news_format': selected_commands[0],
            'model': model
        }
        
    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        
        log_to_csv(
            source_type="VIDEO",
            input_file_name=os.path.basename(video_file_path),
            input_file_size_mb=file_size_mb,
            languages=["te"],
            news_format="ERROR",
            location=town,
            incident_time=incident_time,
            ai_model="N/A",
            output_files=[],
            audio_generated=False,
            status="FAILED",
            notes=f"Error: {str(e)}"
        )
        
        return {
            'status': 'FAILED',
            'error': str(e)
        }
