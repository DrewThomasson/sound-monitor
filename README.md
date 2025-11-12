# Sound Monitor - Noise Pollution Documentation Tool

I hate loud cars so I made an application LOG WHEN THEY ARE TOO LOUD.

### Professional Statatment:

An app for monitoring, recording, and documenting noise pollution to present evidence to city councils or other authorities.

<img width="672" height="449" alt="image" src="https://github.com/user-attachments/assets/1aec8be2-3b0e-4c67-8a7b-dc6f8a29e07e" />


## GUI

| | |
|---|---|
| <img width="748" height="427" alt="Screenshot_20251110_211147" src="https://github.com/user-attachments/assets/dcefb6eb-4419-4408-b60b-a959c838b871" /> | <img width="748" height="427" alt="Screenshot_20251110_211240" src="https://github.com/user-attachments/assets/f3c1c68a-1311-461d-b54b-0fcb433e59a4" /> |
| <img width="748" height="427" alt="Screenshot_20251110_211408" src="https://github.com/user-attachments/assets/29847413-8c6e-43f0-89df-2e62535504ef" /> | <img width="748" height="427" alt="Screenshot_20251110_211444" src="https://github.com/user-attachments/assets/d58fc2e6-6abe-4934-abd7-059c0d4107e9" /> |



## Features

### Audio Recording & Storage
- **Continuous Recording**: Records audio continuously from your selected microphone

### Sound Detection & Logging
- **Real-time Decibel Monitoring**: Tracks sound levels continuously
- **Low-Frequency Detection**: Specifically identifies low-frequency noise like car rumble (20-200 Hz)


### Install

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

The application creates the following structure at runtime:

```
sound-monitor/
├── sound_monitor.py          # Main application (1030+ lines, handles GUI, audio processing, database)
├── run.py                    # Launcher script with dependency checks
├── requirements.txt          # Python dependencies
├── setup.py                  # Installation script
├── test_sound_monitor.py     # Test suite
├── example_demo.py           # Demo with sample data
│
├── recordings/               # Audio recordings directory (created at runtime)
│   ├── YYYYMMDD_HHMMSS.mp3         # Regular 1-minute audio segments
│   ├── event_YYYYMMDD_HHMMSS_ffffff.mp3   # Detected loud events with pre/post buffers
│   └── temp_*.wav            # Temporary WAV files (cleaned up after MP3 conversion)
│
├── videos/                   # Video recordings directory (created at runtime, optional)
│   ├── event_YYYYMMDD_HHMMSS_ffffff.mp4   # Video recordings of loud events with synchronized audio
│   └── ...
│
└── sound_events.db           # SQLite database with event logs
    └── events table:
        - id (PRIMARY KEY)
        - timestamp (event time)
        - duration (event length in seconds)
        - peak_db (highest dB level)
        - avg_db (average dB level)
        - filename (audio file path)
        - video_filename (optional video file path)
        - low_frequency (boolean, car rumble detection)
```


## Technical Details

- **Sample Rate**: 44.1 kHz
- **Format**: 16-bit PCM (recording), MP3 64kbps (storage)
- **Channels**: Mono
- **Chunk Size**: 1024 samples
- **Segment Duration**: 60 seconds
- **dB Calculation**: RMS-based, referenced to max int16 value, calibrated to ~94 dB SPL
- **Low-Frequency Detection**: FFT-based, 20-200 Hz range, >40% energy threshold

## Support

For issues, questions, or suggestions, please open an issue on GitHub.
