# Installation Guide - Sound Monitor

This guide provides step-by-step installation instructions for the Sound Monitor application on different platforms.

## Table of Contents
- [System Requirements](#system-requirements)
- [Linux Installation](#linux-installation)
- [macOS Installation](#macos-installation)
- [Windows Installation](#windows-installation)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## System Requirements

- Python 3.7 or higher
- Microphone or audio input device
- At least 1 GB of free disk space (recommended: 70+ GB for extended recording)
- Operating System: Linux, macOS, or Windows

## Linux Installation

### Ubuntu/Debian

1. **Update package list:**
   ```bash
   sudo apt-get update
   ```

2. **Install system dependencies:**
   ```bash
   sudo apt-get install -y python3 python3-pip python3-pyaudio \
       portaudio19-dev ffmpeg mpg123
   ```

3. **Clone the repository:**
   ```bash
   git clone https://github.com/DrewThomasson/sound-monitor.git
   cd sound-monitor
   ```

4. **Install Python dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

5. **Optional: Install system monitoring:**
   ```bash
   pip3 install psutil
   ```

### Fedora/RHEL/CentOS

1. **Install system dependencies:**
   ```bash
   sudo dnf install python3 python3-pip portaudio-devel \
       ffmpeg mpg123
   ```

2. **Follow steps 3-5 from Ubuntu/Debian above**

### Arch Linux

1. **Install system dependencies:**
   ```bash
   sudo pacman -S python python-pip portaudio ffmpeg mpg123
   ```

2. **Follow steps 3-5 from Ubuntu/Debian above**

## macOS Installation

### Using Homebrew (Recommended)

1. **Install Homebrew (if not already installed):**
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Install dependencies:**
   ```bash
   brew install python portaudio ffmpeg
   ```

3. **Clone the repository:**
   ```bash
   git clone https://github.com/DrewThomasson/sound-monitor.git
   cd sound-monitor
   ```

4. **Install Python dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

5. **Optional: Install system monitoring:**
   ```bash
   pip3 install psutil
   ```

### Using MacPorts

1. **Install dependencies:**
   ```bash
   sudo port install python39 py39-pip portaudio ffmpeg
   ```

2. **Follow steps 3-5 from Homebrew instructions above**

## Windows Installation

### Method 1: Using pip (Recommended)

1. **Install Python:**
   - Download Python 3.7+ from [python.org](https://www.python.org/downloads/)
   - During installation, check "Add Python to PATH"

2. **Install FFmpeg:**
   - Download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Extract to `C:\ffmpeg`
   - Add `C:\ffmpeg\bin` to system PATH

3. **Open Command Prompt and clone repository:**
   ```cmd
   git clone https://github.com/DrewThomasson/sound-monitor.git
   cd sound-monitor
   ```

4. **Install Python dependencies:**
   ```cmd
   pip install -r requirements.txt
   ```

5. **Optional: Install system monitoring:**
   ```cmd
   pip install psutil
   ```

### Method 2: Using Conda/Anaconda

1. **Install Anaconda:**
   - Download from [anaconda.com](https://www.anaconda.com/products/distribution)

2. **Create environment:**
   ```cmd
   conda create -n sound-monitor python=3.9
   conda activate sound-monitor
   ```

3. **Install FFmpeg:**
   ```cmd
   conda install -c conda-forge ffmpeg
   ```

4. **Clone and install:**
   ```cmd
   git clone https://github.com/DrewThomasson/sound-monitor.git
   cd sound-monitor
   pip install -r requirements.txt
   ```

## Verification

After installation, verify everything works:

1. **Run the test suite:**
   ```bash
   python3 test_sound_monitor.py
   ```
   
   You should see all tests pass (PyAudio warning is normal in environments without audio hardware).

2. **Run the demo:**
   ```bash
   python3 example_demo.py
   ```
   
   This creates sample data and demonstrates the database functionality.

3. **Launch the application:**
   ```bash
   python3 sound_monitor.py
   # or
   python3 run.py
   ```

## Troubleshooting

### PyAudio Installation Issues

**Linux:**
```bash
# If pip install fails, try:
sudo apt-get install python3-pyaudio
```

**macOS:**
```bash
# If pip install fails:
brew install portaudio
pip3 install --global-option='build_ext' \
    --global-option='-I/usr/local/include' \
    --global-option='-L/usr/local/lib' pyaudio
```

**Windows:**
```cmd
# Use pre-compiled wheel:
pip install pipwin
pipwin install pyaudio
```

### FFmpeg Not Found

**Linux:**
```bash
which ffmpeg
# If not found:
sudo apt-get install ffmpeg
```

**macOS:**
```bash
which ffmpeg
# If not found:
brew install ffmpeg
```

**Windows:**
- Ensure FFmpeg is in system PATH
- Restart Command Prompt after adding to PATH
- Test with: `ffmpeg -version`

### Permission Denied for Microphone

**Linux:**
```bash
# Add user to audio group:
sudo usermod -a -G audio $USER
# Log out and back in
```

**macOS:**
- Go to System Preferences → Security & Privacy → Privacy → Microphone
- Allow Terminal or Python to access microphone

**Windows:**
- Go to Settings → Privacy → Microphone
- Allow apps to access microphone

### Qt Platform Plugin Issues

**Linux:**
```bash
sudo apt-get install qt5-default
export QT_QPA_PLATFORM=xcb
```

**macOS:**
- Usually works out of the box with PyQt5

**Windows:**
- Reinstall PyQt5:
  ```cmd
  pip uninstall PyQt5
  pip install PyQt5
  ```

### Audio Device Not Listed

1. **Check system recognizes device:**
   - **Linux:** `arecord -l`
   - **macOS:** System Preferences → Sound → Input
   - **Windows:** Settings → System → Sound → Input

2. **Restart the application** after connecting microphone

3. **Test with system tools:**
   ```bash
   # Linux
   arecord -d 5 test.wav
   
   # macOS
   rec -d 5 test.wav
   ```

## Getting Help

If you encounter issues not covered here:

1. Check the [README.md](README.md) for general information
2. Review error messages carefully
3. Ensure all dependencies are installed
4. Try running with verbose output: `python3 -v sound_monitor.py`
5. Open an issue on GitHub with:
   - Your operating system and version
   - Python version (`python3 --version`)
   - Error messages
   - Steps to reproduce

## Next Steps

Once installed, see the [README.md](README.md) for usage instructions and best practices.
