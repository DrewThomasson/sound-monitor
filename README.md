# Sound Monitor - Noise Pollution Documentation Tool

A comprehensive application for monitoring, recording, and documenting noise pollution to present evidence to city councils or other authorities.

<img width="672" height="449" alt="image" src="https://github.com/user-attachments/assets/1aec8be2-3b0e-4c67-8a7b-dc6f8a29e07e" />


## Features

### Audio Recording & Storage
- **Continuous Recording**: Records audio continuously from your selected microphone

### Sound Detection & Logging
- **Real-time Decibel Monitoring**: Tracks sound levels continuously
- **Low-Frequency Detection**: Specifically identifies low-frequency noise like car rumble (20-200 Hz)

### User Interface


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
