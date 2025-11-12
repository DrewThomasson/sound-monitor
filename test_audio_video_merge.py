#!/usr/bin/env python3
"""
Test for audio-video merging functionality
"""

import sys
import os
import tempfile
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_ffmpeg_available():
    """Test that FFmpeg is available"""
    print("Testing FFmpeg availability...")
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )
        if result.returncode == 0:
            print("✓ FFmpeg is installed and working")
            return True
        else:
            print("✗ FFmpeg returned error code")
            return False
    except FileNotFoundError:
        print("✗ FFmpeg not found - install it with: sudo apt-get install ffmpeg")
        return False
    except Exception as e:
        print(f"✗ Error checking FFmpeg: {e}")
        return False


def test_merge_logic():
    """Test the audio-video merge logic"""
    print("\nTesting merge logic...")
    
    # Mock the AudioProcessor class to test merge_audio_video method
    from sound_monitor import AudioProcessor
    from PyQt5.QtCore import QObject
    
    processor = AudioProcessor()
    
    # Test with non-existent files
    result = processor.merge_audio_video(None, "video.mp4")
    if result == "video.mp4":
        print("✓ Handles None audio file correctly")
    else:
        print("✗ Failed to handle None audio file")
        return False
    
    result = processor.merge_audio_video("audio.mp3", None)
    if result is None:
        print("✓ Handles None video file correctly")
    else:
        print("✗ Failed to handle None video file")
        return False
    
    # Test with non-existent file paths
    result = processor.merge_audio_video("/tmp/nonexistent_audio.mp3", "/tmp/nonexistent_video.mp4")
    if result == "/tmp/nonexistent_video.mp4":
        print("✓ Handles non-existent files correctly")
    else:
        print("✗ Failed to handle non-existent files")
        return False
    
    print("✓ Basic merge logic tests passed")
    return True


def create_test_audio():
    """Create a test audio file using FFmpeg"""
    print("\nCreating test audio file...")
    try:
        audio_file = "/tmp/test_audio.mp3"
        # Create a 2-second sine wave audio file
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi',
            '-i', 'sine=frequency=440:duration=2',
            '-b:a', '64k',
            audio_file
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        if result.returncode == 0 and os.path.exists(audio_file):
            print(f"✓ Created test audio: {audio_file}")
            return audio_file
        else:
            print("✗ Failed to create test audio")
            return None
    except Exception as e:
        print(f"✗ Error creating test audio: {e}")
        return None


def create_test_video():
    """Create a test video file using FFmpeg"""
    print("Creating test video file...")
    try:
        video_file = "/tmp/test_video.mp4"
        # Create a 2-second test video (color bars)
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi',
            '-i', 'testsrc=duration=2:size=640x480:rate=10',
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            video_file
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        if result.returncode == 0 and os.path.exists(video_file):
            print(f"✓ Created test video: {video_file}")
            return video_file
        else:
            print("✗ Failed to create test video")
            return None
    except Exception as e:
        print(f"✗ Error creating test video: {e}")
        return None


def test_actual_merge(audio_file, video_file):
    """Test actual merging of audio and video"""
    print("\nTesting actual audio-video merge...")
    try:
        from sound_monitor import AudioProcessor
        
        processor = AudioProcessor()
        
        # Test the merge
        result = processor.merge_audio_video(audio_file, video_file)
        
        if result and os.path.exists(result):
            # Check if the result has audio
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type', '-of', 'default=noprint_wrappers=1', result]
            probe_result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
            output = probe_result.stdout.decode('utf-8')
            
            has_video = 'codec_type=video' in output
            has_audio = 'codec_type=audio' in output
            
            if has_video and has_audio:
                print(f"✓ Merged video has both audio and video streams")
                print(f"  Output file: {result}")
                return True
            elif has_video and not has_audio:
                print(f"⚠ Warning: Merged video has no audio stream (FFmpeg may have failed silently)")
                return False
            else:
                print(f"✗ Merged video is invalid")
                return False
        else:
            print("✗ Merge failed - no output file")
            return False
            
    except Exception as e:
        print(f"✗ Error during merge test: {e}")
        import traceback
        traceback.print_exc()
        return False


def cleanup_test_files():
    """Clean up test files"""
    print("\nCleaning up test files...")
    for f in ['/tmp/test_audio.mp3', '/tmp/test_video.mp4']:
        if os.path.exists(f):
            try:
                os.remove(f)
                print(f"✓ Removed {f}")
            except:
                print(f"⚠ Could not remove {f}")


def main():
    """Run all tests"""
    print("="*60)
    print("Audio-Video Merge Test Suite")
    print("="*60)
    
    all_passed = True
    
    # Check FFmpeg availability
    if not test_ffmpeg_available():
        print("\n⚠ FFmpeg is required for audio-video merging")
        print("Install with: sudo apt-get install ffmpeg")
        return 1
    
    # Test basic logic
    if not test_merge_logic():
        all_passed = False
    
    # Create test files and test actual merge
    audio_file = create_test_audio()
    video_file = create_test_video()
    
    if audio_file and video_file:
        if not test_actual_merge(audio_file, video_file):
            all_passed = False
    else:
        print("\n⚠ Could not create test files, skipping merge test")
        all_passed = False
    
    # Cleanup
    cleanup_test_files()
    
    # Summary
    print("\n" + "="*60)
    if all_passed:
        print("✓ All tests passed!")
        print("="*60)
        return 0
    else:
        print("✗ Some tests failed")
        print("="*60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
