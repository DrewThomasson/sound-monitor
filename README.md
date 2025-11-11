# Sound Monitor - Noise Pollution Documentation Tool

A comprehensive application for monitoring, recording, and documenting noise pollution to present evidence to city councils or other authorities.

![Sound Monitor Application](screenshot.png)

## Features

### Audio Recording & Storage
- **Continuous Recording**: Records audio continuously from your selected microphone
- **Efficient MP3 Compression**: Uses 64kbps MP3 encoding to maximize storage (approximately 28.8 MB per hour)
- **Smart Organization**: Files organized with timestamps for easy retrieval
- **Storage Estimation**: Shows remaining recording capacity based on available disk space

### Sound Detection & Logging
- **Real-time Decibel Monitoring**: Tracks sound levels continuously
- **Intelligent Event Detection**: Automatically identifies and flags sounds above threshold
- **Extended Event Clips**: Records 2 seconds before and after events for full context (4+ seconds minimum)
- **Comprehensive Logging**: Stores timestamp, duration, peak dB, average dB, and file reference for each event
- **SQLite Database**: Fast, efficient storage for quick searches and analysis
- **Low-Frequency Detection**: Specifically identifies low-frequency noise like car rumble (20-200 Hz)
- **Wind Noise Filter**: Optional high-pass filter to reduce false alarms from wind noise (configurable cutoff frequency)

### User Interface
- **Live Waveform Visualization**: See audio waveform in real-time
- **Decibel Meter**: Visual color-coded meter showing current sound levels
- **Device Selection**: Easy dropdown to select your microphone
- **Recording Controls**: Simple start/stop interface
- **Threshold Adjustment**: Slider to set detection sensitivity (40-120 dB)
- **Microphone Calibration**: Offset adjustment for accurate measurements
- **Wind Filter Controls**: Enable/disable wind filtering and adjust cutoff frequency

### Logs & Playback
- **Event Log Table**: View all recorded events in a sortable table
- **Analytics Tab**: Visual charts showing events over time, dB distribution, hourly patterns, and frequency types
- **Smart Filtering**: Filter events by minimum decibel level
- **Sort by Any Column**: Click headers to sort by timestamp, duration, or dB level
- **Audio Playback**: Double-click any event to play the recorded audio (includes pre/post buffers)
- **CSV Export**: Export logs for presentations or further analysis

### Statistics & Monitoring
- **Recording Statistics**: Total recording time, number of events, average/peak dB
- **Low-Frequency Event Count**: Track rumbling vehicles separately
- **Storage Information**: Monitor disk usage and estimated recording capacity
- **System Status**: Battery and resource monitoring for outdoor deployment
- **Non-Intrusive Notifications**: Visual notification panel for extreme events (no popups!)

## Installation

### Requirements
- Python 3.7 or higher
- PyAudio (requires PortAudio)
- FFmpeg (for MP3 encoding)

### System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install python3-pyaudio portaudio19-dev ffmpeg
```

**macOS:**
```bash
brew install portaudio ffmpeg
```

**Windows:**
- Download and install [FFmpeg](https://ffmpeg.org/download.html)
- PyAudio wheels available via pip

### Python Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install PyQt5 pyaudio pydub numpy matplotlib scipy
```

### Optional Dependencies

For system monitoring features (battery status, CPU/memory usage):
```bash
pip install psutil
```

## Usage

### Starting the Application

```bash
python sound_monitor.py
```

### Quick Start Guide

1. **Select Your Microphone**
   - Choose your input device from the dropdown menu
   - The application will list all available input devices

2. **Calibrate (Optional but Recommended)**
   - Go to the Settings tab
   - Use a calibrated sound level meter as reference
   - Adjust the calibration offset until readings match

3. **Set Detection Threshold**
   - Use the threshold slider to set your desired sensitivity
   - Typical values: 60-70 dB for general noise, 80-90 dB for loud events
   - Green: quiet, Yellow: moderate, Orange: loud, Red: very loud

4. **Start Recording**
   - Click "Start Recording" button (green)
   - The button turns red while recording
   - Live waveform and dB meter update in real-time

5. **Monitor Events**
   - Switch to "Event Log" tab to see detected events
   - Events are automatically logged when sound exceeds threshold
   - Filter by minimum dB to focus on louder events

6. **Review and Export**
   - Double-click any event to play the audio
   - Click "Export to CSV" to create a report
   - Use exported data for presentations to city council

### Best Practices

**For Outdoor Deployment:**
- Use a laptop with good battery life
- Place microphone in weather-protected location
- Check "System Status" tab for battery monitoring
- Consider using an external USB microphone for better quality
- **Enable wind noise filter** if experiencing false alarms from wind (Settings tab)

**Dealing with Wind Noise:**
- Wind noise is a common issue in outdoor monitoring, appearing as low-frequency rumble
- Enable the **Wind Noise Filter** in the Settings tab to reduce false alarms
- Recommended cutoff frequencies:
  - **80 Hz (default)**: Good balance for most outdoor conditions
  - **60 Hz**: More aggressive filtering for very windy conditions
  - **100 Hz**: Less aggressive, preserves more low-frequency sounds
- Note: Wind filtering may reduce detection of very low-frequency sounds like distant traffic
- For best results, combine wind filtering with:
  - Physical windscreen on microphone (foam cover)
  - Sheltered microphone placement (away from direct wind)
  - Threshold adjustment to avoid detecting minor wind gusts

**For Evidence Collection:**
- Calibrate your microphone for accurate dB readings
- Set threshold just above normal ambient noise (e.g., 70 dB)
- Let the system run continuously for several days/weeks
- Export logs with timestamp and dB data for official presentations

**Storage Management:**
- Monitor the Settings tab for storage usage
- With 70GB available and 64kbps MP3, you can record approximately 50+ days
- Older recordings can be backed up and deleted to free space

## File Organization

The application creates the following structure:

```
sound-monitor/
├── sound_monitor.py          # Main application
├── requirements.txt          # Python dependencies
├── sound_events.db          # SQLite database with event logs
└── recordings/              # Audio recordings
    ├── 20240315_143022.mp3         # Regular 1-minute segments
    ├── event_20240315_143045.mp3   # Detected loud events
    └── ...
```

## Troubleshooting

### "No audio devices found"
- Ensure your microphone is properly connected
- Check system sound settings
- On Linux, verify ALSA/PulseAudio configuration

### Qt plugin error (Linux/Manjaro with video recording)
If you see `qt.qpa.plugin: Could not load the Qt platform plugin "xcb"`:
- The application automatically fixes this conflict between OpenCV and PyQt5
- If using an older version, update to the latest commit
- Or run: `unset QT_QPA_PLATFORM_PLUGIN_PATH && python3 sound_monitor.py`
- Alternative: `pip uninstall opencv-python && pip install opencv-python-headless`

### "Recording error: [Errno -9981] Input overflowed"
- This is usually harmless and automatically handled
- Consider reducing the buffer size if it happens frequently

### "Cannot import pyaudio"
- Install system audio libraries (see Installation section)
- On Windows, use precompiled wheels: `pip install pipwin && pipwin install pyaudio`

### Audio playback not working
- **Linux**: Install mpg123: `sudo apt-get install mpg123`
- **macOS**: Built-in afplay should work automatically
- **Windows**: Should use default media player

## Technical Details

- **Sample Rate**: 44.1 kHz
- **Format**: 16-bit PCM (recording), MP3 64kbps (storage)
- **Channels**: Mono
- **Chunk Size**: 1024 samples
- **Segment Duration**: 60 seconds
- **dB Calculation**: RMS-based, referenced to max int16 value, calibrated to ~94 dB SPL
- **Low-Frequency Detection**: FFT-based, 20-200 Hz range, >40% energy threshold

## Contributing

Contributions are welcome! Areas for enhancement:
- Support for stereo recording
- Advanced frequency analysis and filtering
- Cloud backup integration
- Mobile app companion
- Machine learning for noise source classification

## License

MIT License - See LICENSE file for details

## Author

Created to document noise pollution and help residents get a good night's sleep.

## Support

For issues, questions, or suggestions, please open an issue on GitHub.
