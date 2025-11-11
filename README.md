# Sound Monitor - Noise Pollution Documentation Tool

A comprehensive application for monitoring, recording, and documenting noise pollution to present evidence to city councils or other authorities.

<img width="672" height="449" alt="image" src="https://github.com/user-attachments/assets/1aec8be2-3b0e-4c67-8a7b-dc6f8a29e07e" />


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

### User Interface
- **Live Waveform Visualization**: See audio waveform in real-time
- **Decibel Meter**: Visual color-coded meter showing current sound levels
- **Device Selection**: Easy dropdown to select your microphone
- **Recording Controls**: Simple start/stop interface
- **Threshold Adjustment**: Slider to set detection sensitivity (40-120 dB)
- **Microphone Calibration**: Offset adjustment for accurate measurements

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


## Usage

### Starting the Application

```bash
python run.py
```

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

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or suggestions, please open an issue on GitHub.
