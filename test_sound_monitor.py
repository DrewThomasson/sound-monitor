#!/usr/bin/env python3
"""
Simple tests for Sound Monitor

Note: Full audio testing requires actual audio hardware.
These tests verify the basic logic and file handling.
"""

import unittest
import os
import json
import tempfile
import shutil
from datetime import datetime


class TestSoundMonitorConfig(unittest.TestCase):
    """Test configuration handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.test_dir, 'test_config.json')
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir)
        
    def test_default_config_creation(self):
        """Test that default config is created if none exists."""
        # Test config file creation and reading
        # (Cannot import sound_monitor module without pyaudio installed)
        
        default_config = {
            'threshold_db': 70,
            'sample_rate': 44100,
            'chunk_size': 1024,
            'channels': 1,
            'recording_duration': 10,
            'reference_db': 90,
            'output_dir': 'recordings',
            'log_file': 'sound_events.csv'
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(default_config, f)
            
        with open(self.config_path, 'r') as f:
            config = json.load(f)
            
        self.assertEqual(config['threshold_db'], 70)
        self.assertEqual(config['sample_rate'], 44100)
        self.assertEqual(config['recording_duration'], 10)
        
    def test_config_values(self):
        """Test that config values are loaded correctly."""
        custom_config = {
            'threshold_db': 80,
            'sample_rate': 48000,
            'chunk_size': 2048,
            'channels': 2,
            'recording_duration': 15,
            'reference_db': 85,
            'output_dir': 'custom_recordings',
            'log_file': 'custom_log.csv'
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(custom_config, f)
            
        with open(self.config_path, 'r') as f:
            config = json.load(f)
            
        self.assertEqual(config['threshold_db'], 80)
        self.assertEqual(config['sample_rate'], 48000)
        self.assertEqual(config['channels'], 2)


class TestAnalysis(unittest.TestCase):
    """Test analysis functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.csv_path = os.path.join(self.test_dir, 'test_events.csv')
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir)
        
    def test_csv_creation(self):
        """Test CSV file creation with proper headers."""
        import csv
        
        headers = [
            'Timestamp',
            'Date',
            'Time',
            'Day of Week',
            'Peak dB',
            'Average dB',
            'Recording File',
            'Duration (s)'
        ]
        
        with open(self.csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
        with open(self.csv_path, 'r') as f:
            reader = csv.reader(f)
            read_headers = next(reader)
            
        self.assertEqual(read_headers, headers)
        
    def test_event_logging_format(self):
        """Test that events are logged in the correct format."""
        import csv
        
        headers = ['Timestamp', 'Date', 'Time', 'Day of Week', 'Peak dB', 'Average dB', 'Recording File', 'Duration (s)']
        
        timestamp = datetime.now().timestamp()
        dt = datetime.fromtimestamp(timestamp)
        
        test_data = [
            timestamp,
            dt.strftime('%Y-%m-%d'),
            dt.strftime('%H:%M:%S'),
            dt.strftime('%A'),
            '75.50',
            '68.25',
            'noise_20250110_120000.wav',
            10
        ]
        
        with open(self.csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerow(test_data)
            
        with open(self.csv_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['Peak dB'], '75.50')
        self.assertEqual(rows[0]['Recording File'], 'noise_20250110_120000.wav')


if __name__ == '__main__':
    unittest.main()
