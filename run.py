#!/usr/bin/env python3
"""
Launcher script for Sound Monitor application
Checks dependencies and starts the application
"""

import sys
import subprocess


def check_dependencies():
    """Check if all required dependencies are installed"""
    missing = []
    
    # Required packages
    required = [
        ('PyQt5', 'PyQt5'),
        ('numpy', 'numpy'),
        ('matplotlib', 'matplotlib'),
        ('pydub', 'pydub'),
        ('scipy', 'scipy'),
    ]
    
    # Check audio library (may not be available in all environments)
    try:
        import pyaudio
    except ImportError:
        print("Warning: pyaudio not installed. Audio recording will not work.")
        print("Install with: pip install pyaudio")
        print("On Linux: sudo apt-get install python3-pyaudio portaudio19-dev")
        print("On macOS: brew install portaudio && pip install pyaudio")
        print()
    
    # Check required packages
    for package_name, import_name in required:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package_name)
    
    if missing:
        print("Missing required packages:")
        for package in missing:
            print(f"  - {package}")
        print("\nInstall with:")
        print("  pip install -r requirements.txt")
        return False
    
    return True


def main():
    """Launch the application"""
    print("Sound Monitor - Noise Pollution Documentation Tool")
    print("="*60)
    
    # Check dependencies
    if not check_dependencies():
        print("\nPlease install missing dependencies before running.")
        return 1
    
    print("Starting application...")
    print()
    
    # Import and run the main application
    try:
        from sound_monitor import main as app_main
        app_main()
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
