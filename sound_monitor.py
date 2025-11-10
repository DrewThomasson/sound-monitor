#!/usr/bin/env python3
"""
Sound Monitor - Professional Noise Monitoring and Recording Application

This application monitors ambient sound levels and automatically records audio
when the decibel level exceeds a configured threshold. All events are logged
to a CSV file for analysis and presentation.

Author: Sound Monitor Contributors
License: Apache 2.0
"""

import pyaudio
import numpy as np
import wave
import csv
import json
import os
import signal
import sys
from datetime import datetime
from pathlib import Path


class SoundMonitor:
    """Main sound monitoring class."""
    
    def __init__(self, config_path='config.json'):
        """Initialize the sound monitor with configuration."""
        self.running = False
        self.load_config(config_path)
        self.setup_directories()
        self.setup_audio()
        self.setup_csv_log()
        
    def load_config(self, config_path):
        """Load configuration from JSON file."""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            # Default configuration
            config = {
                'threshold_db': 70,
                'sample_rate': 44100,
                'chunk_size': 1024,
                'channels': 1,
                'recording_duration': 10,
                'reference_db': 90,
                'output_dir': 'recordings',
                'log_file': 'sound_events.csv'
            }
            # Save default config
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
            print(f"Created default configuration file: {config_path}")
        
        self.threshold_db = config['threshold_db']
        self.sample_rate = config['sample_rate']
        self.chunk_size = config['chunk_size']
        self.channels = config['channels']
        self.recording_duration = config['recording_duration']
        self.reference_db = config['reference_db']
        self.output_dir = config['output_dir']
        self.log_file = config['log_file']
        
    def setup_directories(self):
        """Create necessary directories for output."""
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
    def setup_audio(self):
        """Initialize PyAudio."""
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        
    def setup_csv_log(self):
        """Setup CSV logging file with headers."""
        file_exists = os.path.exists(self.log_file)
        self.csv_file = open(self.log_file, 'a', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        
        if not file_exists:
            self.csv_writer.writerow([
                'Timestamp',
                'Date',
                'Time',
                'Day of Week',
                'Peak dB',
                'Average dB',
                'Recording File',
                'Duration (s)'
            ])
            self.csv_file.flush()
            
    def calculate_db(self, audio_data):
        """Calculate decibel level from audio data."""
        # Convert to numpy array
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        
        # Calculate RMS (Root Mean Square)
        if len(audio_array) == 0:
            return 0
            
        rms = np.sqrt(np.mean(np.square(audio_array.astype(float))))
        
        # Avoid log(0)
        if rms == 0:
            return 0
            
        # Convert to decibels
        # Reference: typical microphone input reference
        db = 20 * np.log10(rms / 1.0) + self.reference_db
        
        return max(0, db)  # Ensure non-negative
        
    def record_audio(self, duration, filename):
        """Record audio for specified duration and save to file."""
        print(f"🔴 Recording: {filename}")
        
        frames = []
        db_levels = []
        
        num_chunks = int(self.sample_rate / self.chunk_size * duration)
        
        for _ in range(num_chunks):
            try:
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                frames.append(data)
                db_levels.append(self.calculate_db(data))
            except Exception as e:
                print(f"Error reading audio: {e}")
                break
                
        # Save to WAV file
        filepath = os.path.join(self.output_dir, filename)
        with wave.open(filepath, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(frames))
            
        peak_db = max(db_levels) if db_levels else 0
        avg_db = np.mean(db_levels) if db_levels else 0
        
        return peak_db, avg_db
        
    def log_event(self, timestamp, peak_db, avg_db, filename, duration):
        """Log sound event to CSV file."""
        dt = datetime.fromtimestamp(timestamp)
        
        self.csv_writer.writerow([
            timestamp,
            dt.strftime('%Y-%m-%d'),
            dt.strftime('%H:%M:%S'),
            dt.strftime('%A'),
            f'{peak_db:.2f}',
            f'{avg_db:.2f}',
            filename,
            duration
        ])
        self.csv_file.flush()
        
    def monitor(self):
        """Main monitoring loop."""
        print("=" * 60)
        print("Sound Monitor - Noise Detection and Recording System")
        print("=" * 60)
        print(f"Threshold: {self.threshold_db} dB")
        print(f"Recording Duration: {self.recording_duration} seconds")
        print(f"Output Directory: {self.output_dir}")
        print(f"Log File: {self.log_file}")
        print("=" * 60)
        print("Monitoring started. Press Ctrl+C to stop.")
        print()
        
        self.running = True
        consecutive_quiet = 0
        in_recording = False
        
        try:
            while self.running:
                # Read audio chunk
                try:
                    data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                except Exception as e:
                    print(f"Error reading audio stream: {e}")
                    continue
                    
                # Calculate current dB level
                current_db = self.calculate_db(data)
                
                # Display current level every 10 quiet chunks
                if not in_recording:
                    consecutive_quiet += 1
                    if consecutive_quiet >= 10:
                        print(f"Current level: {current_db:.2f} dB (Threshold: {self.threshold_db} dB)", end='\r')
                        consecutive_quiet = 0
                
                # Check if threshold exceeded
                if current_db >= self.threshold_db and not in_recording:
                    in_recording = True
                    timestamp = datetime.now().timestamp()
                    dt = datetime.now()
                    
                    filename = f"noise_{dt.strftime('%Y%m%d_%H%M%S')}.wav"
                    
                    print(f"\n⚠️  LOUD NOISE DETECTED: {current_db:.2f} dB at {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # Record audio
                    peak_db, avg_db = self.record_audio(self.recording_duration, filename)
                    
                    # Log event
                    self.log_event(timestamp, peak_db, avg_db, filename, self.recording_duration)
                    
                    print(f"✅ Recorded: Peak={peak_db:.2f} dB, Average={avg_db:.2f} dB")
                    print(f"   Saved to: {os.path.join(self.output_dir, filename)}\n")
                    
                    in_recording = False
                    consecutive_quiet = 0
                    
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user.")
        finally:
            self.cleanup()
            
    def cleanup(self):
        """Clean up resources."""
        print("Cleaning up...")
        if hasattr(self, 'stream') and self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if hasattr(self, 'audio') and self.audio:
            self.audio.terminate()
        if hasattr(self, 'csv_file') and self.csv_file:
            self.csv_file.close()
        print("Cleanup complete.")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Sound Monitor - Professional Noise Detection and Recording System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 sound_monitor.py              # Run with default config.json
  python3 sound_monitor.py --config custom.json  # Use custom config

For more information, see README.md and QUICKSTART.md
        """
    )
    
    parser.add_argument(
        '--config',
        default='config.json',
        help='Path to configuration file (default: config.json)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Sound Monitor 1.0.0'
    )
    
    args = parser.parse_args()
    
    try:
        monitor = SoundMonitor(config_path=args.config)
        monitor.monitor()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
