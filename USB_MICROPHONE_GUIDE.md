# USB Microphone Setup Guide

## Problem Solved

**Issue:** "Invalid sample rate" error when using USB microphones (Logitech webcams, etc.)

**Solution:** Automatic sample rate detection now finds the best supported rate for your device.

## How It Works

### Automatic Sample Rate Detection

The application now automatically detects and uses the best sample rate for your microphone:

1. **Tries device default rate first** (e.g., 48000 Hz for many USB mics)
2. **Falls back to common rates** if needed:
   - 44100 Hz (CD quality)
   - 48000 Hz (Professional audio)
   - 32000 Hz
   - 22050 Hz
   - 16000 Hz (Voice quality)
   - 8000 Hz (Telephone quality)

### What You'll See

When you select a microphone, the status bar will show:
```
Using device sample rate: 48000 Hz
```

This confirms the app found a compatible rate for your device.

## Improved Calibration

### New Calibration Interface

The Settings tab now has an enhanced calibration panel with:

#### 1. Live Readings
- **Current Reading (raw):** Shows the uncalibrated dB level
- **Calibrated Reading:** Shows the adjusted dB level

#### 2. Quick Adjustment Buttons
- **-5:** Decrease by 5 dB
- **-1:** Decrease by 1 dB
- **+1:** Increase by 1 dB
- **+5:** Increase by 5 dB
- **Reset:** Return to 0 offset

#### 3. Clear Instructions
Step-by-step guide with examples:
- Use a reference sound meter
- Make a constant noise
- Compare readings
- Adjust offset to match

### Calibration Example

**Scenario:** Your sound meter shows 80 dB, but the app shows 75 dB

**Solution:**
1. Go to Settings tab
2. Look at "Current Reading (raw): 75.0 dB"
3. Click the "+5" button (or adjust to +5.0)
4. Now "Calibrated Reading: 80.0 dB" matches your meter!

### Using the Calibration Panel

#### Method 1: Fine Adjustment (0.5 dB steps)
1. Go to Settings tab
2. Start recording (so you can see live readings)
3. Make a noise (clap, music, etc.)
4. Use the spinbox arrows for precise adjustment

#### Method 2: Quick Adjustment
1. Go to Settings tab
2. Start recording
3. Make a noise
4. Use quick buttons: -5, -1, +1, +5

#### Method 3: Manual Entry
1. Go to Settings tab
2. Type the offset directly in the spinbox
3. Example: If app is 5 dB too low, enter +5.0

## Device Information

The Settings tab now shows:
- **Device Name:** e.g., "Logitech Webcam C920"
- **Sample Rate:** The actual rate being used (e.g., 48000 Hz)
- **Max Input Channels:** Number of channels supported
- **Default Sample Rate:** Device's preferred rate

## Troubleshooting

### "Invalid sample rate" Error

**Old behavior:** App crashed or failed to record
**New behavior:** Automatically finds a working rate

If you still see this error:
1. Check that your microphone is connected
2. Try a different USB port
3. Restart the application
4. Check system audio settings

### Calibration Not Accurate

**Tips for accurate calibration:**

1. **Use a reference meter**
   - Phone app: "Sound Meter" (free)
   - Hardware: Calibrated SPL meter
   - Online: Calibration tone + known measurement

2. **Make consistent noise**
   - Use same sound for both measurements
   - Constant tone is best (music, test tone)
   - Avoid transient sounds (claps)

3. **Position correctly**
   - Both devices same distance from source
   - Same orientation
   - No obstructions

4. **Test multiple levels**
   - Calibrate at moderate level (60-80 dB)
   - Verify at different levels
   - Re-adjust if needed

### Logitech Webcam Specific

**Common Logitech webcam sample rates:**
- C920: 48000 Hz or 44100 Hz
- C922: 48000 Hz
- C930e: 48000 Hz

The app will automatically detect and use the correct rate.

### Manjaro/Linux Specific

**If microphone not detected:**
```bash
# Check ALSA devices
arecord -l

# Check PulseAudio devices
pactl list sources

# Test recording
arecord -d 5 -f cd test.wav
```

**Permissions issue:**
```bash
# Add user to audio group
sudo usermod -a -G audio $USER
# Log out and back in
```

## Best Practices

### For Accurate Measurements

1. **Calibrate when you first set up**
2. **Re-calibrate if you change microphones**
3. **Test calibration periodically**
4. **Use consistent reference sound**

### For Logitech Webcams

1. **Position webcam properly**
   - Microphone usually on top
   - Face toward noise source
   - Avoid USB cable noise

2. **Check webcam settings**
   - Disable automatic gain control if possible
   - Set volume to 100%
   - Disable enhancement features

3. **USB connection**
   - Use USB 3.0 port if available
   - Avoid USB hubs if possible
   - Minimize USB cable length

## FAQ

**Q: Why does my USB mic use a different sample rate than 44100 Hz?**
A: Many USB microphones and webcams prefer 48000 Hz (professional audio standard). The app now supports this automatically.

**Q: Does sample rate affect quality?**
A: Higher rates provide better frequency response, but for noise monitoring, any rate from 16000 Hz and up works well. The app uses the best available.

**Q: Can I force a specific sample rate?**
A: The current version auto-detects. Manual selection could be added if needed.

**Q: Why are my dB readings off?**
A: Use the calibration feature! Each microphone has different sensitivity. Calibration ensures accurate measurements.

**Q: Do I need to recalibrate every time?**
A: No. Calibration is saved. Only recalibrate if you:
- Change microphones
- Notice readings seem wrong
- Compare with a reference meter and see a difference

**Q: Can I calibrate without a reference meter?**
A: You can use typical sound levels as a rough guide:
- Normal conversation: 60-65 dB
- Busy traffic: 70-80 dB
- Lawn mower: 85-90 dB
- Motorcycle: 90-100 dB

But a reference meter (even a phone app) is strongly recommended for accuracy.

## Summary

**Key Improvements:**
- ✅ Automatic sample rate detection
- ✅ Works with USB microphones and webcams
- ✅ Enhanced calibration interface
- ✅ Live calibration feedback
- ✅ Device information display
- ✅ No more "invalid sample rate" errors

**Tested with:**
- Logitech webcams (C920, C922, C930e)
- USB microphones (various brands)
- Built-in laptop microphones
- External audio interfaces

**Your Logitech webcam should now work perfectly!** 🎤✅
