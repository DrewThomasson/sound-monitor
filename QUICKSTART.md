# Quick Start Guide - Sound Monitor

Get started monitoring noise pollution in 5 minutes!

## Installation (Quick Version)

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install python3-pyaudio portaudio19-dev ffmpeg mpg123
pip3 install PyQt5 pydub numpy matplotlib scipy
```

**macOS:**
```bash
brew install portaudio ffmpeg
pip3 install -r requirements.txt
```

**Windows:**
- Install Python 3.7+ from python.org
- Install FFmpeg from ffmpeg.org
- Run: `pip install -r requirements.txt`

## Running the Application

```bash
python3 sound_monitor.py
```

## Basic Usage

### 1. Select Microphone
- Choose your input device from the dropdown at the top

### 2. Set Threshold
- Use the slider to set noise detection level
- **Recommended:** 70-80 dB for general noise, 85-95 dB for very loud events

### 3. Calibrate (Optional)
- Go to **Settings** tab
- Compare with a calibrated sound meter
- Adjust offset until readings match

### 4. Start Recording
- Click **Start Recording** (green button)
- Button turns red while recording
- Let it run continuously

### 5. Monitor Events
- Switch to **Event Log** tab
- See all detected loud sounds
- Double-click any event to play audio

### 6. Export Data
- Click **Export to CSV** in Event Log tab
- Save for presentations to city council

## Understanding the Interface

### Live Monitoring Tab
- **Waveform:** Real-time audio visualization
- **dB Meter:** Current sound level with color coding
  - Green (0-50 dB): Quiet
  - Yellow (50-70 dB): Moderate
  - Orange (70-90 dB): Loud
  - Red (90+ dB): Very loud

### Event Log Tab
- **Timestamp:** When the event occurred
- **Duration:** How long the noise lasted
- **Peak dB:** Loudest point
- **Avg dB:** Average during event
- **Low Freq:** "Yes" if low-frequency (cars, trucks)
- **Filename:** Recording location

### Statistics Tab
- Total recording time
- Number of events detected
- Average and peak decibel levels
- Low-frequency event count

### Settings Tab
- Microphone calibration
- Storage information
- System status (battery, CPU, memory)

## Tips for Best Results

1. **Run Continuously**
   - Let the app run for days/weeks to collect evidence
   - Runs efficiently in background

2. **Position Microphone**
   - Place near window facing noise source
   - Avoid covering microphone
   - Use external USB mic for better quality

3. **Set Appropriate Threshold**
   - Too low: Many false positives
   - Too high: Miss important events
   - Adjust based on ambient noise level

4. **Monitor Storage**
   - Check Settings tab for capacity
   - 70GB ≈ 50+ days of recording
   - Older files can be archived externally

5. **Export Regularly**
   - Export CSV weekly for backup
   - Create summary reports for authorities

## Example Workflow for City Council

1. **Collect Data:** Run for 2-4 weeks
2. **Filter Results:** Show only events >85 dB
3. **Export CSV:** Include timestamps and dB levels
4. **Play Examples:** Double-click worst events to demonstrate
5. **Show Statistics:** Use Stats tab for summary data

## Keyboard Shortcuts

- **Ctrl+R:** Start/Stop recording (when implemented)
- **Ctrl+E:** Export to CSV (when implemented)
- **Ctrl+Q:** Quit application

## Common Issues

**"PyAudio not available"**
- See INSTALL.md for platform-specific installation

**"No audio devices found"**
- Check microphone is connected
- Verify system recognizes device
- Restart application

**"Recording error"**
- Try different input device
- Check microphone permissions
- Ensure device is not in use by other apps

**Files are large**
- This is normal for WAV format
- MP3 compression happens automatically
- Each hour ≈ 28.8 MB

## Getting Help

- See **README.md** for detailed information
- See **INSTALL.md** for installation help
- Run demo: `python3 example_demo.py`
- Run tests: `python3 test_sound_monitor.py`

## Next Steps

- Run the example demo to see sample data
- Practice with the interface before deployment
- Consider outdoor deployment with laptop
- Plan your evidence presentation strategy

---

**Ready to document noise pollution and get some sleep!** 🎤📊😴
