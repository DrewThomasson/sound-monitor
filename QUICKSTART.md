# Quick Start Guide - Sound Monitor

## Installation (Manjaro Linux)

```bash
# 1. Install system dependencies
sudo pacman -S python python-pip portaudio

# 2. Install Python packages
pip install -r requirements.txt
```

## Basic Usage

```bash
# Start monitoring (default: 70 dB threshold)
python3 sound_monitor.py
```

The monitor will:
- ✅ Display current sound levels in real-time
- ✅ Automatically record 10-second clips when noise exceeds 70 dB
- ✅ Save recordings to `recordings/` folder
- ✅ Log all events to `sound_events.csv`

Press `Ctrl+C` to stop.

## Customizing the Threshold

Edit `config.json` and change `threshold_db`:

```json
{
    "threshold_db": 65,  // Lower = more sensitive
    ...
}
```

Recommended values:
- **50-60 dB**: Very quiet, catches normal conversation
- **60-70 dB**: Residential area, catches loud talking/TV
- **70-80 dB**: Heavy traffic, loud vehicles (default)
- **80+ dB**: Only extremely loud noises

## Viewing Your Data

### Quick Analysis

```bash
python3 analyze.py
```

This shows:
- Total events recorded
- Loudest events
- Events by day of week
- Events by time of day
- Late night disturbances (11 PM - 6 AM)

### Detailed Analysis

Open `sound_events.csv` in Excel/LibreOffice/Google Sheets:

```bash
# On Manjaro
libreoffice sound_events.csv
```

Create charts and summaries for your presentation.

## Running Continuously

To run overnight or for extended periods:

```bash
# Option 1: Using nohup (runs in background)
nohup python3 sound_monitor.py > monitor.log 2>&1 &

# Option 2: Using screen (recommended)
screen -S sound_monitor
python3 sound_monitor.py
# Press Ctrl+A then D to detach
# Later: screen -r sound_monitor to reattach
```

## Troubleshooting

### "No microphone found"

```bash
# Check if microphone is detected
arecord -l

# May need to install/restart PulseAudio
sudo pacman -S pulseaudio pulseaudio-alsa
pulseaudio --kill
pulseaudio --start
```

### Not recording when it should

- Increase microphone volume in system settings
- Lower `threshold_db` in `config.json`
- Check microphone is not muted
- Try different microphone if available

### Recording too often

- Raise `threshold_db` in `config.json`
- Move microphone away from computer fans/noise sources
- Close windows if outdoor noise is triggering it

## Tips for Best Results

1. **Test your threshold**: Run the monitor during normal conditions and when you hear the noise you want to capture. Adjust threshold accordingly.

2. **Position microphone**: Place near window if noise is from outside. Keep away from computer fans and other local noise sources.

3. **Run for full week**: Collect data for at least 7 days to show patterns (weekday vs weekend, time of day, etc.)

4. **Keep the loudest recordings**: Use `analyze.py` to identify the loudest events, then include those audio files in your presentation.

5. **Document everything**: Note the dates, times, and what you heard. This adds context to the data.

## Example Presentation to Council

Your evidence package should include:

1. **Summary Report** (from `analyze.py`)
   - Total events over monitoring period
   - Peak noise levels and times
   - Late night disturbances

2. **CSV Data** (`sound_events.csv`)
   - Opened in spreadsheet with charts
   - Highlight patterns (weekends, specific times)

3. **Audio Samples** (top 5-10 loudest from `recordings/`)
   - Play the most egregious examples
   - Note the timestamps and decibel levels

4. **Your Testimony**
   - How it affects your sleep
   - Health impacts
   - Request for enforcement

Good luck! 🎯
