# Sound Monitor

A professional noise monitoring and recording application for documenting excessive noise events.

## Overview

Sound Monitor is a Python application that continuously monitors ambient sound levels and automatically records audio when noise exceeds a configurable decibel threshold. All events are logged with timestamps, decibel measurements, and audio recordings - perfect for presenting evidence to city councils or noise ordinance enforcement.

## Features

- **Continuous Monitoring**: Real-time sound level monitoring
- **Automatic Recording**: Captures audio when noise exceeds threshold
- **Detailed Logging**: CSV logs with timestamps, dates, times, day of week, and decibel levels
- **Professional Output**: Organized data suitable for formal presentation
- **Configurable Settings**: Customize threshold, recording duration, and more
- **Audio Evidence**: Saves WAV recordings of each loud event

## Installation

### Prerequisites

For Manjaro Linux and other Arch-based systems:

```bash
# Install system dependencies
sudo pacman -S python python-pip portaudio

# Install Python packages
pip install -r requirements.txt
```

For Ubuntu/Debian:

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install python3 python3-pip portaudio19-dev

# Install Python packages
pip install -r requirements.txt
```

For macOS:

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install PortAudio
brew install portaudio

# Install Python packages
pip install -r requirements.txt
```

## Configuration

Edit `config.json` to customize the monitoring behavior:

```json
{
    "threshold_db": 70,           // Decibel threshold for recording (adjust based on your needs)
    "sample_rate": 44100,         // Audio sample rate (CD quality)
    "chunk_size": 1024,           // Audio buffer size
    "channels": 1,                // Mono audio (1) or stereo (2)
    "recording_duration": 10,     // Seconds to record after threshold exceeded
    "reference_db": 90,           // Reference decibel level for calibration
    "output_dir": "recordings",   // Directory for audio files
    "log_file": "sound_events.csv" // CSV log file name
}
```

### Recommended Threshold Settings

- **Quiet neighborhood at night**: 50-60 dB
- **Residential area**: 60-70 dB
- **Heavy traffic or loud vehicles**: 70-80 dB
- **Construction or very loud noise**: 80+ dB

## Usage

### Basic Usage

Run the monitor with default settings:

```bash
python3 sound_monitor.py
```

### Running as a Background Service

To run continuously in the background:

```bash
# Using nohup
nohup python3 sound_monitor.py > monitor.log 2>&1 &

# Or using screen (install with: sudo pacman -S screen)
screen -S sound_monitor
python3 sound_monitor.py
# Press Ctrl+A then D to detach
```

### Stopping the Monitor

Press `Ctrl+C` to stop monitoring gracefully.

## Output Files

### CSV Log (`sound_events.csv`)

The CSV file contains:
- **Timestamp**: Unix timestamp
- **Date**: Calendar date (YYYY-MM-DD)
- **Time**: Time of day (HH:MM:SS)
- **Day of Week**: Monday, Tuesday, etc.
- **Peak dB**: Maximum decibel level during recording
- **Average dB**: Average decibel level during recording
- **Recording File**: Name of the audio file
- **Duration**: Length of recording in seconds

### Audio Recordings (`recordings/`)

WAV files named with timestamp pattern: `noise_YYYYMMDD_HHMMSS.wav`

## Presenting Your Data

### For City Council or Noise Ordinance Enforcement

1. **Open the CSV file** in Excel, Google Sheets, or LibreOffice Calc
2. **Create summary statistics**:
   - Count of events by day of week
   - Peak noise times (sort by time)
   - Average and maximum decibel levels
   - Charts showing noise patterns over time
3. **Include audio samples**: Select the loudest recordings as evidence
4. **Document patterns**: Highlight recurring issues (e.g., "15 events above 80dB between 11pm-2am on weekends")

### Sample Analysis Commands

```bash
# Count total events
wc -l sound_events.csv

# Show loudest events
sort -t',' -k5 -rn sound_events.csv | head -10

# Events by day of week
cut -d',' -f4 sound_events.csv | sort | uniq -c
```

## Troubleshooting

### "No Default Input Device" Error

Your system may not have a microphone detected:

```bash
# Test microphone on Linux
arecord -l

# On Manjaro, you may need to install PulseAudio
sudo pacman -S pulseaudio pulseaudio-alsa
```

### Permission Denied for Audio Device

```bash
# Add your user to the audio group
sudo usermod -aG audio $USER
# Log out and log back in
```

### Low Sensitivity / Not Recording

- Increase your microphone input level in system settings
- Lower the `threshold_db` value in `config.json`
- Adjust the `reference_db` value (higher = more sensitive)

### Too Many False Triggers

- Raise the `threshold_db` value in `config.json`
- Ensure background noise is minimized
- Position microphone away from fans, computers, etc.

## Technical Details

### Decibel Calculation

The application calculates decibel levels using:
1. RMS (Root Mean Square) of audio samples
2. Logarithmic conversion to decibel scale
3. Reference adjustment for microphone input

Note: These are relative measurements. For legally certified measurements, use a calibrated sound level meter.

## License

Apache License 2.0 - See LICENSE file for details

## Contributing

Contributions welcome! Please feel free to submit issues or pull requests.

## Safety and Legal Notes

- This tool provides estimates, not certified measurements
- For legal proceedings, consult with local noise ordinance requirements
- Some jurisdictions may require certified sound level meters
- Check local laws regarding audio recording and privacy
- Use recordings responsibly and in accordance with local regulations
