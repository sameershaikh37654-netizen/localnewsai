# """File Manager for NewsBot - Handles input/output organization"""

# import os
# import json
# import shutil
# from typing import Tuple, Optional

# class FileManager:
#     def __init__(self, base_dir: str = None):
#         if base_dir is None:
#             base_dir = os.path.join(os.path.expanduser("~"), "Desktop", "NewsBot")
        
#         self.base_dir = base_dir
#         self.input_dir = os.path.join(base_dir, "input")
#         self.output_dir = os.path.join(base_dir, "output")
#         self.counter_file = os.path.join(base_dir, "counters.json")
        
#         self._create_structure()
    
#     def _create_structure(self):
#         for media_type in ["image", "audio", "video"]:
#             os.makedirs(os.path.join(self.input_dir, media_type), exist_ok=True)
#             os.makedirs(os.path.join(self.output_dir, media_type), exist_ok=True)
#         os.makedirs(os.path.join(self.output_dir, "scripts"), exist_ok=True)
    
#     def load_counters(self) -> dict:
#         if os.path.exists(self.counter_file):
#             try:
#                 with open(self.counter_file, 'r') as f:
#                     return json.load(f)
#             except:
#                 pass
#         return {"image": 0, "audio": 0, "video": 0}
    
#     def save_counters(self, counters: dict):
#         with open(self.counter_file, 'w') as f:
#             json.dump(counters, f, indent=2)
    
#     def get_next_prefix(self, media_type: str) -> str:
#         counters = self.load_counters()
#         counters[media_type] = counters.get(media_type, 0) + 1
#         self.save_counters(counters)
        
#         prefix_map = {"image": "i", "audio": "a", "video": "v"}
#         return f"{prefix_map[media_type]}{counters[media_type]}"
    
#     def save_input_file(self, temp_path: str, media_type: str) -> Tuple[str, str]:
#         try:
#             file_prefix = self.get_next_prefix(media_type)
#             ext = os.path.splitext(temp_path)[1]
#             input_filename = f"{file_prefix}_input{ext}"
#             input_path = os.path.join(self.input_dir, media_type, input_filename)
            
#             shutil.copy2(temp_path, input_path)
#             print(f"✅ Input saved: {input_filename}")
#             return input_path, file_prefix
#         except Exception as e:
#             print(f"❌ Save failed: {e}")
#             return None, None
    
#     def get_output_paths(self, file_prefix: str, media_type: str) -> dict:
#         return {
#             "script": os.path.join(self.output_dir, "scripts", f"{file_prefix}_script.txt"),
#             "audio": os.path.join(self.output_dir, media_type, f"{file_prefix}_audio.mp3")
#         }
    
#     def move_to_output(self, temp_script_path: str, temp_audio_path: Optional[str],
#                       file_prefix: str, media_type: str) -> dict:
#         output_paths = self.get_output_paths(file_prefix, media_type)
#         final_paths = {}
        
#         try:
#             if temp_script_path and os.path.exists(temp_script_path):
#                 shutil.move(temp_script_path, output_paths["script"])
#                 final_paths["script"] = output_paths["script"]
#                 print(f"✅ Script: {file_prefix}_script.txt")
            
#             if temp_audio_path and os.path.exists(temp_audio_path):
#                 shutil.move(temp_audio_path, output_paths["audio"])
#                 final_paths["audio"] = output_paths["audio"]
#                 print(f"✅ Audio: {file_prefix}_audio.mp3")
            
#             return final_paths
#         except Exception as e:
#             print(f"❌ Move failed: {e}")
#             return final_paths
    
#     def reset_counters(self):
#         self.save_counters({"image": 0, "audio": 0, "video": 0})
#         print("✅ Counters reset to 0")
    
#     def sync_counters_with_files(self):
#         """Sync counters with actual files in input directory"""
#         counters = {"image": 0, "audio": 0, "video": 0}
#         prefix_map = {"image": "i", "audio": "a", "video": "v"}
        
#         for media_type in ["image", "audio", "video"]:
#             input_dir = os.path.join(self.input_dir, media_type)
#             if os.path.exists(input_dir):
#                 files = [f for f in os.listdir(input_dir) 
#                         if f.startswith(f"{prefix_map[media_type]}") and "_input" in f]
                
#                 # Extract numbers from filenames
#                 numbers = []
#                 for f in files:
#                     try:
#                         num = int(f.split('_')[0][1:])  # Extract number after prefix
#                         numbers.append(num)
#                     except:
#                         pass
                
#                 # Set counter to highest number found
#                 if numbers:
#                     counters[media_type] = max(numbers)
        
#         self.save_counters(counters)
#         print(f"✅ Synced: 🖼️{counters['image']} 🎵{counters['audio']} 🎬{counters['video']}")
    
#     def get_stats(self) -> dict:
#         counters = self.load_counters()
#         return {
#             "total_files": sum(counters.values()),
#             "images": counters.get("image", 0),
#             "audio": counters.get("audio", 0),
#             "videos": counters.get("video", 0),
#             "base_dir": self.base_dir
#         }



"""File Manager for NewsBot - Handles input/output organization with gap filling"""

import os
import json
import shutil
from typing import Tuple, Optional

class FileManager:
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = os.path.join(os.path.expanduser("~"), "Desktop", "NewsBot")
        
        self.base_dir = base_dir
        self.input_dir = os.path.join(base_dir, "input")
        self.output_dir = os.path.join(base_dir, "output")
        self.counter_file = os.path.join(base_dir, "counters.json")
        
        self._create_structure()
    
    def _create_structure(self):
        """Create directory structure"""
        for media_type in ["image", "audio", "video"]:
            os.makedirs(os.path.join(self.input_dir, media_type), exist_ok=True)
            os.makedirs(os.path.join(self.output_dir, media_type), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "scripts"), exist_ok=True)
    
    def _get_existing_numbers(self, media_type: str) -> set:
        """
        Get all existing file numbers for a media type by checking input directory
        Returns a set of numbers that are currently in use
        """
        input_dir = os.path.join(self.input_dir, media_type)
        prefix_map = {"image": "i", "audio": "a", "video": "v"}
        prefix = prefix_map[media_type]
        
        existing_numbers = set()
        
        if os.path.exists(input_dir):
            files = os.listdir(input_dir)
            for filename in files:
                # Look for files like "i1_input.jpg", "a2_input.mp3", etc.
                if filename.startswith(f"{prefix}") and "_input" in filename:
                    try:
                        # Extract number from filename (e.g., "i1_input.jpg" -> 1)
                        number_part = filename.split('_')[0][len(prefix):]  # Remove prefix
                        number = int(number_part)
                        existing_numbers.add(number)
                    except (ValueError, IndexError):
                        continue
        
        return existing_numbers
    
    def _find_next_available_number(self, media_type: str) -> int:
        """
        Find the next available number (filling gaps first)
        If files are i1, i3, i4 (i2 was deleted), this returns 2
        If files are i1, i2, i3, this returns 4
        """
        existing = self._get_existing_numbers(media_type)
        
        if not existing:
            return 1
        
        # Find the first gap in the sequence
        for num in range(1, max(existing) + 2):
            if num not in existing:
                return num
        
        # This should never be reached, but just in case
        return max(existing) + 1
    
    def load_counters(self) -> dict:
        """Load counters (kept for backward compatibility, but not used for numbering)"""
        if os.path.exists(self.counter_file):
            try:
                with open(self.counter_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"image": 0, "audio": 0, "video": 0}
    
    def save_counters(self, counters: dict):
        """Save counters (kept for backward compatibility)"""
        with open(self.counter_file, 'w') as f:
            json.dump(counters, f, indent=2)
    
    def get_next_prefix(self, media_type: str) -> str:
        """
        Get next available prefix, filling gaps if files were deleted
        Examples:
        - Files: i1, i2, i3 → Returns: i4
        - Files: i1, i3, i4 (i2 deleted) → Returns: i2
        - Files: (empty) → Returns: i1
        """
        next_number = self._find_next_available_number(media_type)
        prefix_map = {"image": "i", "audio": "a", "video": "v"}
        prefix = f"{prefix_map[media_type]}{next_number}"
        
        print(f"📋 Next available: {prefix}")
        return prefix
    
    def save_input_file(self, temp_path: str, media_type: str) -> Tuple[str, str]:
        """Save input file with next available number"""
        try:
            file_prefix = self.get_next_prefix(media_type)
            ext = os.path.splitext(temp_path)[1]
            input_filename = f"{file_prefix}_input{ext}"
            input_path = os.path.join(self.input_dir, media_type, input_filename)
            
            shutil.copy2(temp_path, input_path)
            print(f"✅ Input saved: {input_filename}")
            return input_path, file_prefix
        except Exception as e:
            print(f"❌ Save failed: {e}")
            return None, None
    
    def get_output_paths(self, file_prefix: str, media_type: str) -> dict:
        """Get output file paths for a given prefix"""
        return {
            "script": os.path.join(self.output_dir, "scripts", f"{file_prefix}_script.txt"),
            "audio": os.path.join(self.output_dir, media_type, f"{file_prefix}_audio.mp3")
        }
    
    def move_to_output(self, temp_script_path: str, temp_audio_path: Optional[str],
                      file_prefix: str, media_type: str) -> dict:
        """Move processed files to output directory"""
        output_paths = self.get_output_paths(file_prefix, media_type)
        final_paths = {}
        
        try:
            if temp_script_path and os.path.exists(temp_script_path):
                shutil.move(temp_script_path, output_paths["script"])
                final_paths["script"] = output_paths["script"]
                print(f"✅ Script: {file_prefix}_script.txt")
            
            if temp_audio_path and os.path.exists(temp_audio_path):
                shutil.move(temp_audio_path, output_paths["audio"])
                final_paths["audio"] = output_paths["audio"]
                print(f"✅ Audio: {file_prefix}_audio.mp3")
            
            return final_paths
        except Exception as e:
            print(f"❌ Move failed: {e}")
            return final_paths
    
    def reset_counters(self):
        """Reset counters (kept for backward compatibility)"""
        self.save_counters({"image": 0, "audio": 0, "video": 0})
        print("✅ Counters reset to 0")
    
    def sync_counters_with_files(self):
        """
        Sync counters with actual files (for display purposes)
        Shows current file counts
        """
        stats = {
            "image": len(self._get_existing_numbers("image")),
            "audio": len(self._get_existing_numbers("audio")),
            "video": len(self._get_existing_numbers("video"))
        }
        
        # Show which numbers are in use
        for media_type in ["image", "audio", "video"]:
            existing = sorted(self._get_existing_numbers(media_type))
            prefix_map = {"image": "i", "audio": "a", "video": "v"}
            emoji_map = {"image": "🖼️", "audio": "🎵", "video": "🎬"}
            
            if existing:
                files_str = ", ".join([f"{prefix_map[media_type]}{n}" for n in existing])
                print(f"{emoji_map[media_type]} {media_type.capitalize()}: {files_str}")
            else:
                print(f"{emoji_map[media_type]} {media_type.capitalize()}: (none)")
        
        print(f"✅ Total: 🖼️{stats['image']} 🎵{stats['audio']} 🎬{stats['video']}")
    
    def get_stats(self) -> dict:
        """Get statistics about stored files"""
        image_count = len(self._get_existing_numbers("image"))
        audio_count = len(self._get_existing_numbers("audio"))
        video_count = len(self._get_existing_numbers("video"))
        
        return {
            "total_files": image_count + audio_count + video_count,
            "images": image_count,
            "audio": audio_count,
            "videos": video_count,
            "base_dir": self.base_dir
        }
    
    def list_files(self, media_type: str = None) -> dict:
        """
        List all files with their numbers
        Useful for debugging and seeing which slots are filled
        """
        if media_type:
            media_types = [media_type]
        else:
            media_types = ["image", "audio", "video"]
        
        result = {}
        for mtype in media_types:
            existing = sorted(self._get_existing_numbers(mtype))
            prefix_map = {"image": "i", "audio": "a", "video": "v"}
            
            files = []
            for num in existing:
                prefix = f"{prefix_map[mtype]}{num}"
                files.append(prefix)
            
            result[mtype] = {
                "count": len(files),
                "numbers": existing,
                "files": files,
                "next_available": self._find_next_available_number(mtype)
            }
        
        return result
    
    def check_gaps(self) -> dict:
        """
        Check for gaps in numbering
        Returns info about missing numbers
        """
        gaps = {}
        
        for media_type in ["image", "audio", "video"]:
            existing = sorted(self._get_existing_numbers(media_type))
            
            if not existing:
                gaps[media_type] = []
                continue
            
            # Find gaps in the sequence
            missing = []
            for num in range(1, max(existing)):
                if num not in existing:
                    missing.append(num)
            
            gaps[media_type] = missing
        
        return gaps


# Testing function
if __name__ == "__main__":
    fm = FileManager()
    
    print("="*60)
    print("FILE MANAGER TEST")
    print("="*60)
    
    # Show current stats
    stats = fm.get_stats()
    print(f"\n📊 Current Stats:")
    print(f"   Total: {stats['total_files']}")
    print(f"   🖼️ Images: {stats['images']}")
    print(f"   🎵 Audio: {stats['audio']}")
    print(f"   🎬 Videos: {stats['videos']}")
    
    # List all files
    print(f"\n📁 File Listing:")
    file_list = fm.list_files()
    for media_type, info in file_list.items():
        print(f"\n{media_type.upper()}:")
        print(f"   Count: {info['count']}")
        print(f"   Numbers in use: {info['numbers']}")
        print(f"   Files: {', '.join(info['files']) if info['files'] else '(none)'}")
        print(f"   Next available: {media_type[0]}{info['next_available']}")
    
    # Check for gaps
    print(f"\n🔍 Gap Analysis:")
    gaps = fm.check_gaps()
    for media_type, missing in gaps.items():
        if missing:
            print(f"   {media_type}: Missing {missing}")
        else:
            print(f"   {media_type}: No gaps")
    
    print("\n" + "="*60)
