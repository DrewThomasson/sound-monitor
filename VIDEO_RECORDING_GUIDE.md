# Video Recording Guide

## Overview

The Sound Monitor application now supports **event-based video recording with audio** to provide complete audiovisual evidence for noise pollution documentation.

## Key Features

### Smart Event-Based Recording
- **Only records during loud events** (above threshold)
- **Not continuous** - saves massive amounts of storage
- Automatically starts when noise exceeds threshold
- Continues during entire loud event
- Stops when noise returns to normal
- **Video includes synchronized audio** - complete evidence in one file

### Storage Optimization
- **Resolution:** 640x480 (VGA) - balance between quality and size
- **Frame Rate:** 10 FPS - sufficient for evidence, minimal storage
- **Codec:** MP4V (video) + AAC (audio) - widely compatible
- **Approximate Size:** 5-10 MB per minute of event video
- **Example:** 70GB storage = hundreds of event videos

### Integration
- Synchronized audio and video captured for each loud event
- Audio is automatically merged into video files using FFmpeg
- Both standalone audio MP3 files and combined video files are saved
- Live camera preview in the GUI
- Video playback from event log table includes audio

## Setup Instructions

### 1. Install Dependencies

**FFmpeg (Required for audio in videos):**
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

**OpenCV (Required for video recording):**
```bash
pip install opencv-python
```

### 2. Connect Camera
- Connect USB webcam or use built-in laptop camera
- Launch the application
- Camera will be detected automatically

### 3. Enable Video Recording
1. Go to the **Settings** tab
2. Find "📹 Video Recording Settings" section
3. Check "Enable Video Recording on Loud Events"
4. Select your camera from the dropdown
5. Camera preview will appear in the **Live Monitoring** tab

### 4. Test It Out
1. Go to **Live Monitoring** tab
2. See the live camera preview (if enabled)
3. Make a loud noise (above threshold)
4. Video will start recording automatically with audio
5. When noise stops, video+audio saves automatically
6. Double-click the video in the Event Log to play it with audio
3. Make a loud noise (above threshold)
4. Video will start recording automatically
5. When noise stops, video saves automatically

## Using the Feature

### Camera Preview
- Located in the **Live Monitoring** tab
- Shows what the camera sees in real-time
- Only active when video recording is enabled
- Updates at 10 FPS

### Event Log with Video
- Event log table now has a "Video" column
- Shows "📹 Yes" if video was recorded
- Double-click video column to play the video
- Double-click other columns to play audio

### Video Files
- Stored in `videos/` directory
- Named: `event_YYYYMMDD_HHMMSS_ffffff.mp4`
- Matches corresponding audio file naming
- **Contains both video and audio tracks** - complete evidence in one file
- Can be played with any standard video player (VLC, Windows Media Player, etc.)
- Audio is synchronized with video automatically

## Technical Details

### Video Specifications
```
Resolution: 640x480 pixels
Frame Rate: 10 FPS
Video Codec: MP4V
Audio Codec: AAC (merged from event audio)
Format: .mp4
Bitrate: Variable (optimized)
Audio Quality: 64kbps MP3 (converted to AAC in video)
```

### Storage Calculations
```
Audio Only:
- 64kbps MP3 audio
- ~28.8 MB/hour
- 70GB = 50+ days continuous

With Event Videos (estimated):
- If 10 loud events/day averaging 1 minute each
- ~10 minutes of video/day = 50-100 MB/day
- Audio: ~690 MB/day (continuous)
- Total: ~750-800 MB/day
- 70GB = ~90 days of monitoring
```

### Performance Impact
- **CPU Usage:** +2-5% during event recording
- **Memory:** +20-30 MB for camera buffer
- **Disk I/O:** Minimal (writes only during events)
- **GUI Responsiveness:** No impact (threaded)

## Privacy Considerations

### Legal Compliance
- Video surveillance may require:
  - Signage/notifications
  - Neighbor consent (varies by location)
  - Compliance with local laws
- **Recommendation:** Consult local regulations

### Best Practices
- Point camera at noise source, not neighbors
- Focus on sound source (vehicles, construction, etc.)
- Use audio-only mode if privacy is a concern
- Event-based recording is less intrusive than continuous

## Troubleshooting

### Qt Plugin Error (Linux/Manjaro)
If you see an error like:
```
qt.qpa.plugin: Could not load the Qt platform plugin "xcb"
IOT instruction (core dumped)
```

**Solution:** This is a Qt plugin conflict between OpenCV and PyQt5. The latest version of the application automatically fixes this. If you're using an older version, update to the latest commit.

**Manual Fix (if needed):**
```bash
# Unset OpenCV's Qt plugin path before running
unset QT_QPA_PLATFORM_PLUGIN_PATH
python3 sound_monitor.py

# Or use opencv-python-headless
pip uninstall opencv-python
pip install opencv-python-headless
```

### Camera Not Detected
```
- Check if camera is connected
- Try different USB port
- Check camera permissions (Linux/macOS)
- Install camera drivers (Windows)
- On Linux: sudo usermod -a -G video $USER (then logout/login)
```

### "OpenCV not available" Message
```
pip install opencv-python
# Then restart the application
```

### "FFmpeg not found" Warning
```
# Video will be recorded without audio
# To add audio to videos, install FFmpeg:

# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
# Then restart the application
```

### Video Not Recording
```
1. Check "Enable Video Recording" is checked
2. Verify camera is selected
3. Ensure noise exceeds threshold
4. Check videos/ directory permissions
5. Verify FFmpeg is installed (for audio in videos)
```

### Video Has No Audio
```
1. Ensure FFmpeg is installed: ffmpeg -version
2. Check status bar for "FFmpeg not found" message
3. Install FFmpeg (see installation instructions above)
4. Restart the application
5. Previous videos won't have audio retroactively added
```

### Video Won't Play
```
- Install VLC player (recommended)
- Or use mpv, ffplay, or Windows Media Player
- Video files are standard MP4 format
```

### Camera Preview Black/Frozen
```
- Close other apps using the camera
- Select different camera from dropdown
- Restart the application
- Check camera is working in other apps
```

## Tips for Best Results

### Camera Placement
1. **Aim at noise source** - point toward street, construction site, etc.
2. **Stable mounting** - avoid shaky footage
3. **Good lighting** - helps with video quality
4. **Clear view** - no obstructions

### Settings Optimization
1. **Lower threshold** - captures more events (more video)
2. **Higher threshold** - only extreme events (less video)
3. **Test first** - make test noises to verify setup
4. **Monitor storage** - check Statistics tab regularly

### For City Council Presentation
1. **Enable video** for better evidence
2. **Set appropriate threshold** - relevant noise levels
3. **Test placement** - ensure camera captures source
4. **Export CSV logs** - includes video filenames
5. **Save videos** - backup to external drive before presentation

## Comparison: Audio vs Audio+Video

### Audio Only
- ✓ Minimal storage (50+ days on 70GB)
- ✓ No privacy concerns
- ✓ Low CPU usage
- ✗ No visual context
- ✗ Harder to identify source

### Audio + Video (Event-Based)
- ✓ Visual evidence of noise source
- ✓ More convincing for authorities
- ✓ Still efficient (90+ days on 70GB)
- ✓ Only records during events
- ✗ Requires camera
- ✗ Privacy considerations

## FAQ

**Q: Does video record continuously?**
A: No! Only during loud events (above threshold). This saves storage and respects privacy.

**Q: Do videos include audio?**
A: Yes! As of the latest version, videos automatically include the synchronized audio from the event. Both the standalone MP3 file and the video with audio are saved.

**Q: How much storage do videos use?**
A: ~5-10 MB per minute of event video. If you have 10 events per day averaging 1 minute each, that's only 50-100 MB/day.

**Q: Can I use my webcam?**
A: Yes! Built-in laptop webcams and USB webcams both work.

**Q: What if I don't have a camera?**
A: The app works perfectly with audio-only mode. Video is completely optional.

**Q: Can I record video without audio?**
A: No, video is tied to audio events. Video only records when loud sound is detected, and the audio is automatically included in the video file.

**Q: What if FFmpeg is not installed?**
A: Videos will still be recorded but without audio tracks. Install FFmpeg to enable audio in future video recordings.

**Q: How do I disable video?**
A: Uncheck "Enable Video Recording" in the Settings tab.

**Q: Where are videos stored?**
A: In the `videos/` folder next to the `recordings/` folder.

**Q: What format are the videos?**
A: Standard MP4 files with AAC audio that play in any media player.

**Q: Does video recording impact audio quality?**
A: No, audio recording is independent and unchanged. Both the original MP3 and the video with audio are saved.

**Q: Can I change video quality?**
A: Advanced users can edit VIDEO_WIDTH, VIDEO_HEIGHT, and VIDEO_FPS constants in the code.

## Support

For issues or questions:
1. Check this guide
2. Review the main README.md
3. Open an issue on GitHub
4. Check OpenCV documentation

---

**Remember:** Video recording with audio provides complete audiovisual evidence for documenting noise pollution. FFmpeg is required to merge audio into video files. Use responsibly and in compliance with local laws.
