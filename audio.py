# import os
# from datetime import datetime
# import streamlit as st

# from shared_components import (
#     save_upload_to_temp, transcribe_audio, auto_detect_news_type, get_optimal_model,
#     generate_tv_news_script_multilingual, log_to_csv,
#     generate_audio_from_script, VOICE_PRESETS
# )


# def process_audio(audio_file, client, manual_command, lang_hint, town, incident_time,
#                  session_folder=None, file_prefix="a1",
#                  generate_audio=False, sarvam_api_key=None, voice_settings=None):
    
#     file_size_mb = audio_file.size / (1024 * 1024)
#     progress = st.progress(0)
#     status = st.empty()
    
#     try:
#         status.text("🎤 Transcribing audio...")
#         progress.progress(30)
        
#         audio_path = save_upload_to_temp(audio_file)
#         lang = None if lang_hint == "auto" else lang_hint
#         transcript = transcribe_audio(client, audio_path, lang)
        
#         st.success("✓ Audio transcribed")
#         progress.progress(60)
        
#         with st.expander("📋 View Transcript"):
#             st.text_area("Transcript:", transcript, height=150, key=f"transcript_{file_prefix}")
        
#         if manual_command == "AUTO-DETECT":
#             status.text("🤖 Detecting news type...")
#             selected_commands = auto_detect_news_type(transcript, client)
#             st.info(f"Detected: {selected_commands[0]}")
#         else:
#             selected_commands = [manual_command]
        
#         progress.progress(70)
        
#         status.text("📺 Creating Telugu script...")
#         model = get_optimal_model("audio", selected_commands, file_size_mb)
        
#         scripts = generate_tv_news_script_multilingual(
#             client=client, model=model,
#             source_type="audio",
#             command_types=selected_commands,
#             languages=["te"],
#             transcript=transcript,
#             content_analysis=f"Audio transcript:\n{transcript}",
#             town=town or None,
#             incident_time=incident_time or None
#         )
        
#         progress.progress(90)
        
#         status.text("💾 Saving script...")
        
#         if session_folder:
#             audio_folder = os.path.join(session_folder, "audio")
#             os.makedirs(audio_folder, exist_ok=True)
            
#             output_filename = f"{file_prefix}_script.txt"
#             output_path = os.path.join(audio_folder, output_filename)
            
#             with open(output_path, "w", encoding="utf-8") as f:
#                 f.write(scripts["te"])
#         else:
#             from shared_components import save_tv_script_output_multilingual
#             script_paths = save_tv_script_output_multilingual(scripts, "audio", selected_commands)
#             output_path = script_paths["te"]
        
#         audio_output_path = None
#         if generate_audio and sarvam_api_key:
#             try:
#                 status.text("🎙️ Generating TTS audio...")
#                 progress.progress(95)
                
#                 voice_settings = voice_settings or {}
#                 speaker = voice_settings.get('speaker', 'arya')
#                 pitch = voice_settings.get('pitch', 0.0)
#                 pace = voice_settings.get('pace', 1.0)
#                 loudness = voice_settings.get('loudness', 1.0)
#                 sample_rate = voice_settings.get('sample_rate', 22050)
                
#                 if session_folder:
#                     audio_filename = f"{file_prefix}_audio.mp3"
#                     audio_output_path = os.path.join(audio_folder, audio_filename)
#                 else:
#                     audio_output_path = None
                
#                 audio_output_path = generate_audio_from_script(
#                     script_text=scripts["te"],
#                     sarvam_api_key=sarvam_api_key,
#                     speaker=speaker,
#                     pitch=pitch,
#                     pace=pace,
#                     loudness=loudness,
#                     sample_rate=sample_rate,
#                     output_path=audio_output_path
#                 )
                
#                 st.success(f"✅ TTS audio generated with {VOICE_PRESETS[speaker]['name']} voice!")
                
#             except Exception as e:
#                 st.warning(f"⚠️ TTS generation failed: {str(e)}")
#                 audio_output_path = None
        
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
        
#         if audio_output_path and os.path.exists(audio_output_path):
#             with col2:
#                 with open(audio_output_path, "rb") as f:
#                     st.download_button(
#                         "📥 Download TTS Audio (MP3)",
#                         data=f,
#                         file_name=os.path.basename(audio_output_path),
#                         mime="audio/mp3",
#                         key=f"download_audio_{file_prefix}"
#                     )
            
#             st.markdown("### 🔊 Listen to Generated TTS Audio")
#             with open(audio_output_path, "rb") as f:
#                 st.audio(f.read(), format="audio/mp3")
        
#         output_files = [output_path]
#         if audio_output_path:
#             output_files.append(audio_output_path)
        
#         log_to_csv(
#             source_type="AUDIO",
#             input_file_name=audio_file.name,
#             input_file_size_mb=file_size_mb,
#             languages=["te"],
#             news_format=selected_commands[0],
#             location=town,
#             incident_time=incident_time,
#             ai_model=model,
#             output_files=output_files,
#             audio_generated=audio_output_path is not None,
#             status="SUCCESS",
#             notes=f"Prefix: {file_prefix}, Lang: {lang_hint}"
#         )
        
#         return {
#             'status': 'SUCCESS',
#             'output_file': output_path,
#             'audio_file': audio_output_path,
#             'news_format': selected_commands[0],
#             'model': model
#         }
        
#     except Exception as e:
#         status.text("❌ Failed")
#         st.error(f"Error: {str(e)}")
        
#         log_to_csv(
#             source_type="AUDIO",
#             input_file_name=audio_file.name,
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



# audio.py
import os
from datetime import datetime

from shared_components import (
    save_upload_to_temp, transcribe_audio, auto_detect_news_type, get_optimal_model,
    generate_tv_news_script_multilingual, log_to_csv,
    generate_audio_from_script, VOICE_PRESETS
)


def process_audio(audio_file_path, audio_data, client, manual_command, lang_hint, town, incident_time,
                 session_folder=None, file_prefix="a1",
                 generate_audio=False, sarvam_api_key=None, voice_settings=None,target_script_duration=30):
    
    file_size_mb = len(audio_data) / (1024 * 1024)
    
    try:
        print("🎤 Transcribing audio...")
        
        audio_path = save_upload_to_temp(audio_file_path, audio_data)
        lang = None if lang_hint == "auto" else lang_hint
        transcript = transcribe_audio(client, audio_path, lang)
        
        print("✓ Audio transcribed")
        
        print(f"📋 Transcript:\n{transcript}\n")
        
        if manual_command == "AUTO-DETECT":
            print("🤖 Detecting news type...")
            selected_commands = auto_detect_news_type(transcript, client)
            print(f"Detected: {selected_commands[0]}")
        else:
            selected_commands = [manual_command]
        
        # print("📺 Creating Telugu script...")
        # model = get_optimal_model("audio", selected_commands, file_size_mb)
        
        # scripts = generate_tv_news_script_multilingual(
        #     client=client, model=model,
        #     source_type="audio",
        #     command_types=selected_commands,
        #     languages=["te"],
        #     transcript=transcript,
        #     content_analysis=f"Audio transcript:\n{transcript}",
        #     town=town or None,
        #     incident_time=incident_time or None
        # )

        print(f"📺 Creating {target_script_duration}s Telugu script...")
        model = get_optimal_model("audio", selected_commands, file_size_mb)
        
        from shared_components import generate_tv_news_script_multilingual_with_duration
        
        scripts = generate_tv_news_script_multilingual_with_duration(
            client=client, model=model,
            source_type="audio",
            command_types=selected_commands,
            languages=["te"],
            target_duration_seconds=target_script_duration,
            transcript=transcript[:1000] if transcript else None,
            content_analysis=f"Audio transcript:\n{transcript[:1000] if transcript else ''}",
            town=town or None,
            incident_time=incident_time or None
        )
        
        # Rest remains the same with pace adjustment
        pace = voice_settings.get('pace', 1.15) 
        
        print("💾 Saving script...")
        
        if session_folder:
            audio_folder = os.path.join(session_folder, "audio")
            os.makedirs(audio_folder, exist_ok=True)
            
            output_filename = f"{file_prefix}_script.txt"
            output_path = os.path.join(audio_folder, output_filename)
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(scripts["te"])
        else:
            from shared_components import save_tv_script_output_multilingual
            script_paths = save_tv_script_output_multilingual(scripts, "audio", selected_commands)
            output_path = script_paths["te"]
        
        audio_output_path = None
        if generate_audio and sarvam_api_key:
            try:
                print("🎙️ Generating TTS audio...")
                
                voice_settings = voice_settings or {}
                speaker = voice_settings.get('speaker', 'arya')
                pitch = voice_settings.get('pitch', 0.0)
                pace = voice_settings.get('pace', 1.0)
                loudness = voice_settings.get('loudness', 1.0)
                sample_rate = voice_settings.get('sample_rate', 22050)
                
                if session_folder:
                    audio_filename = f"{file_prefix}_audio.mp3"
                    audio_output_path = os.path.join(audio_folder, audio_filename)
                else:
                    audio_output_path = None
                
                audio_output_path = generate_audio_from_script(
                    script_text=scripts["te"],
                    sarvam_api_key=sarvam_api_key,
                    speaker=speaker,
                    pitch=pitch,
                    pace=pace,
                    loudness=loudness,
                    sample_rate=sample_rate,
                    output_path=audio_output_path
                )
                
                print(f"✅ TTS audio generated with {VOICE_PRESETS[speaker]['name']} voice!")
                
            except Exception as e:
                print(f"⚠️ TTS generation failed: {str(e)}")
                audio_output_path = None
        
        print("✅ Complete!")
        
        print("\n📺 Generated Telugu Script:")
        print(scripts["te"])
        print(f"\n📄 Script saved: {output_path}")
        
        if audio_output_path:
            print(f"🔊 Audio saved: {audio_output_path}")
        
        output_files = [output_path]
        if audio_output_path:
            output_files.append(audio_output_path)
        
        log_to_csv(
            source_type="AUDIO",
            input_file_name=os.path.basename(audio_file_path),
            input_file_size_mb=file_size_mb,
            languages=["te"],
            news_format=selected_commands[0],
            location=town,
            incident_time=incident_time,
            ai_model=model,
            output_files=output_files,
            audio_generated=audio_output_path is not None,
            status="SUCCESS",
            notes=f"Prefix: {file_prefix}, Lang: {lang_hint}"
        )
        
        return {
            'status': 'SUCCESS',
            'output_file': output_path,
            'audio_file': audio_output_path,
            'news_format': selected_commands[0],
            'model': model
        }
        
    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        
        log_to_csv(
            source_type="AUDIO",
            input_file_name=os.path.basename(audio_file_path),
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
