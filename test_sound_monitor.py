#!/usr/bin/env python3
"""
Test script for Sound Monitor application
Tests basic functionality without requiring audio hardware
"""

import sys
import os
import sqlite3
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    try:
        import numpy as np
        print("✓ numpy")
    except ImportError as e:
        print(f"✗ numpy: {e}")
        return False
    
    try:
        import PyQt5.QtWidgets
        print("✓ PyQt5")
    except ImportError as e:
        print(f"✗ PyQt5: {e}")
        return False
    
    try:
        import matplotlib
        print("✓ matplotlib")
    except ImportError as e:
        print(f"✗ matplotlib: {e}")
        return False
    
    try:
        from pydub import AudioSegment
        print("✓ pydub")
    except ImportError as e:
        print(f"✗ pydub: {e}")
        return False
    
    try:
        from scipy import signal
        print("✓ scipy")
    except ImportError as e:
        print(f"✗ scipy: {e}")
        return False
    
    # PyAudio is optional for testing
    try:
        import pyaudio
        print("✓ pyaudio")
    except ImportError:
        print("⚠ pyaudio not available (expected in test environment)")
    
    return True


def test_database_operations():
    """Test database creation and operations"""
    print("\nTesting database operations...")
    
    # Use temporary database
    test_db = "test_events.db"
    
    try:
        # Create database
        conn = sqlite3.connect(test_db)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS events
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      timestamp TEXT,
                      duration REAL,
                      peak_db REAL,
                      avg_db REAL,
                      filename TEXT,
                      low_frequency BOOLEAN)''')
        conn.commit()
        print("✓ Database created")
        
        # Insert test event
        c.execute('''INSERT INTO events 
                     (timestamp, duration, peak_db, avg_db, filename, low_frequency)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  ('2024-01-01 12:00:00', 2.5, 85.3, 82.1, 'test.mp3', False))
        conn.commit()
        print("✓ Event inserted")
        
        # Query event
        c.execute('SELECT * FROM events WHERE peak_db >= ?', (80,))
        results = c.fetchall()
        if len(results) == 1:
            print("✓ Event retrieved")
        else:
            print(f"✗ Expected 1 event, got {len(results)}")
            return False
        
        conn.close()
        
        # Clean up
        os.remove(test_db)
        print("✓ Database cleanup")
        
        return True
        
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        if os.path.exists(test_db):
            os.remove(test_db)
        return False


def test_audio_processing():
    """Test audio processing functions"""
    print("\nTesting audio processing...")
    
    try:
        import numpy as np
        
        # Create synthetic audio data
        sample_rate = 44100
        duration = 0.1  # 100ms
        frequency = 440  # A4 note
        
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio_data = (np.sin(2 * np.pi * frequency * t) * 32767 / 2).astype(np.int16)
        
        print("✓ Synthetic audio generated")
        
        # Test dB calculation
        rms = np.sqrt(np.mean(audio_data.astype(np.float64)**2))
        if rms > 0:
            db = 20 * np.log10(rms / 32768.0) + 94
            print(f"✓ dB calculation: {db:.1f} dB")
        else:
            print("✗ RMS calculation failed")
            return False
        
        # Test FFT for frequency detection
        fft = np.fft.rfft(audio_data.astype(np.float64))
        freqs = np.fft.rfftfreq(len(audio_data), 1/sample_rate)
        
        # Find peak frequency
        peak_idx = np.argmax(np.abs(fft))
        peak_freq = freqs[peak_idx]
        
        if abs(peak_freq - frequency) < 5:  # Within 5 Hz
            print(f"✓ FFT analysis: detected {peak_freq:.1f} Hz (expected {frequency} Hz)")
        else:
            print(f"⚠ FFT analysis: detected {peak_freq:.1f} Hz (expected {frequency} Hz)")
        
        return True
        
    except Exception as e:
        print(f"✗ Audio processing test failed: {e}")
        return False


def test_file_structure():
    """Test that recordings directory can be created"""
    print("\nTesting file structure...")
    
    try:
        test_dir = "test_recordings"
        Path(test_dir).mkdir(exist_ok=True)
        
        if os.path.isdir(test_dir):
            print("✓ Directory creation")
            os.rmdir(test_dir)
            print("✓ Directory cleanup")
            return True
        else:
            print("✗ Directory creation failed")
            return False
            
    except Exception as e:
        print(f"✗ File structure test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("Sound Monitor - Test Suite")
    print("="*60)
    
    all_passed = True
    
    # Run tests
    if not test_imports():
        all_passed = False
    
    if not test_database_operations():
        all_passed = False
    
    if not test_audio_processing():
        all_passed = False
    
    if not test_file_structure():
        all_passed = False
    
    # Summary
    print("\n" + "="*60)
    if all_passed:
        print("✓ All tests passed!")
        print("="*60)
        return 0
    else:
        print("✗ Some tests failed")
        print("="*60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
