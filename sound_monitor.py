#!/usr/bin/env python3
"""
Sound Monitor Application
A comprehensive tool for monitoring and documenting noise pollution
"""

import sys
import os
import time
import wave
import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty

import numpy as np
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    pyaudio = None

# Fix Qt plugin conflict between OpenCV and PyQt5
# Must be set BEFORE importing cv2
os.environ.pop('QT_QPA_PLATFORM_PLUGIN_PATH', None)

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QSlider, QTableWidget, QTableWidgetItem,
    QTabWidget, QFileDialog, QMessageBox, QProgressBar, QGroupBox,
    QGridLayout, QSpinBox, QDoubleSpinBox, QCheckBox, QTextEdit
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QPalette, QColor, QImage, QPixmap
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from pydub import AudioSegment
from scipy import signal as scipy_signal


# Constants
CHUNK = 1024
FORMAT = pyaudio.paInt16 if PYAUDIO_AVAILABLE else 8  # 8 is paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 60  # Record in 1-minute segments
MP3_BITRATE = "64k"  # Low bitrate for storage efficiency
DB_FILE = "sound_events.db"
RECORDINGS_DIR = "recordings"
VIDEOS_DIR = "videos"  # Directory for video recordings

# Video settings (optimized for storage and CPU)
VIDEO_WIDTH = 640  # 640x480 is efficient
VIDEO_HEIGHT = 480
VIDEO_FPS = 10  # Low FPS to save storage/CPU
VIDEO_CODEC = 'mp4v'  # Compatible codec


class AudioProcessor(QObject):
    """Handles audio recording, processing, and storage"""
    
    level_updated = pyqtSignal(float, float)  # RMS level, dB level
    event_detected = pyqtSignal(dict)  # Event data
    status_updated = pyqtSignal(str)  # Status messages
    error_occurred = pyqtSignal(str)  # Error messages
    
    def __init__(self):
        super().__init__()
        self.p = None
        self.stream = None
        self.recording = False
        self.device_index = None
        self.device_sample_rate = RATE  # Will be auto-detected per device
        self.threshold_db = 80
        self.calibration_offset = 0
        self.current_segment = []
        self.segment_start_time = None
        self.event_in_progress = False
        self.event_start_time = None
        self.event_peak_db = 0
        self.event_samples = []
        
        # Ring buffer for pre-event context (2 seconds before event)
        self.pre_event_buffer_seconds = 2
        self.post_event_buffer_seconds = 2
        self.audio_ring_buffer = []
        self.max_ring_buffer_samples = int(self.pre_event_buffer_seconds * RATE / CHUNK)
        
        # Video recording attributes
        self.video_enabled = False
        self.camera_index = 0
        self.video_writer = None
        self.video_event_filename = None
        
        # Create recordings and videos directories
        Path(RECORDINGS_DIR).mkdir(exist_ok=True)
        Path(VIDEOS_DIR).mkdir(exist_ok=True)
        
        # Initialize database
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database for event logging"""
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS events
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      timestamp TEXT,
                      duration REAL,
                      peak_db REAL,
                      avg_db REAL,
                      filename TEXT,
                      video_filename TEXT,
                      low_frequency BOOLEAN)''')
        
        # Migration: Add video_filename column if it doesn't exist (for existing databases)
        try:
            c.execute("SELECT video_filename FROM events LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            c.execute("ALTER TABLE events ADD COLUMN video_filename TEXT")
            conn.commit()
            
        conn.commit()
        conn.close()
        
    def get_audio_devices(self):
        """Get list of available audio input devices"""
        if not PYAUDIO_AVAILABLE:
            return []
        
        if self.p is None:
            self.p = pyaudio.PyAudio()
        
        devices = []
        for i in range(self.p.get_device_count()):
            info = self.p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                devices.append((i, info['name']))
        return devices
    
    def get_camera_devices(self):
        """Get list of available camera devices"""
        if not CV2_AVAILABLE:
            return []
        
        cameras = []
        # Try first 10 possible camera indices
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cameras.append((i, f"Camera {i}"))
                cap.release()
        return cameras
    
    def set_camera(self, camera_index):
        """Set the camera device to use for video recording"""
        self.camera_index = camera_index
    
    def set_video_enabled(self, enabled):
        """Enable or disable video recording"""
        self.video_enabled = enabled and CV2_AVAILABLE
    
    def set_camera_widget(self, camera_widget):
        """Set reference to camera preview widget for shared camera access"""
        self.camera_widget = camera_widget
    
    def start_video_recording(self, event_timestamp):
        """Start recording video for an event"""
        if not self.video_enabled or not CV2_AVAILABLE:
            return None
        
        if not hasattr(self, 'camera_widget') or self.camera_widget is None:
            self.error_occurred.emit("Camera preview not initialized")
            return None
        
        try:
            # Create video filename
            video_filename = os.path.join(VIDEOS_DIR, f"event_{event_timestamp}.mp4")
            
            # Initialize video writer
            fourcc = cv2.VideoWriter_fourcc(*VIDEO_CODEC)
            out = cv2.VideoWriter(video_filename, fourcc, VIDEO_FPS, (VIDEO_WIDTH, VIDEO_HEIGHT))
            
            if not out.isOpened():
                self.error_occurred.emit("Cannot create video writer")
                return None
            
            self.video_writer = out
            self.video_event_filename = video_filename
            
            return video_filename
        except Exception as e:
            self.error_occurred.emit(f"Error starting video recording: {str(e)}")
            return None
    
    def write_video_frame(self):
        """Capture and write a single video frame from camera preview"""
        if self.video_writer is None:
            return
        
        if not hasattr(self, 'camera_widget') or self.camera_widget is None:
            return
        
        try:
            # Get frame from camera preview widget (shared camera)
            frame = self.camera_widget.get_current_frame()
            if frame is not None:
                self.video_writer.write(frame)
        except Exception as e:
            self.error_occurred.emit(f"Error writing video frame: {str(e)}")
    
    def stop_video_recording(self):
        """Stop recording video and cleanup"""
        if self.video_writer is not None:
            try:
                self.video_writer.release()
            except:
                pass
            self.video_writer = None
        
        filename = self.video_event_filename
        self.video_event_filename = None
        return filename
    
    def detect_sample_rate(self, device_index):
        """Detect the best supported sample rate for a device"""
        if not PYAUDIO_AVAILABLE:
            return RATE
        
        if self.p is None:
            self.p = pyaudio.PyAudio()
        
        # Common sample rates to try, in order of preference
        preferred_rates = [44100, 48000, 32000, 22050, 16000, 8000]
        
        device_info = self.p.get_device_info_by_index(device_index)
        
        # First try the device's default sample rate
        try:
            default_rate = int(device_info.get('defaultSampleRate', 44100))
            if self.p.is_format_supported(
                default_rate,
                input_device=device_index,
                input_channels=CHANNELS,
                input_format=FORMAT
            ):
                self.status_updated.emit(f"Using device sample rate: {default_rate} Hz")
                return default_rate
        except:
            pass
        
        # Try preferred rates
        for rate in preferred_rates:
            try:
                if self.p.is_format_supported(
                    rate,
                    input_device=device_index,
                    input_channels=CHANNELS,
                    input_format=FORMAT
                ):
                    self.status_updated.emit(f"Using sample rate: {rate} Hz")
                    return rate
            except:
                continue
        
        # If nothing works, return default
        self.error_occurred.emit(f"Could not find supported sample rate, using {RATE} Hz")
        return RATE
    
    def set_device(self, device_index):
        """Set the input device and auto-detect sample rate"""
        self.device_index = device_index
        if device_index is not None:
            self.device_sample_rate = self.detect_sample_rate(device_index)
        else:
            self.device_sample_rate = RATE
        
    def set_threshold(self, threshold_db):
        """Set the detection threshold in dB"""
        self.threshold_db = threshold_db
        
    def set_calibration(self, offset):
        """Set calibration offset for dB readings"""
        self.calibration_offset = offset
        
    def calculate_db(self, audio_data):
        """Calculate decibel level from audio data"""
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        if len(audio_array) == 0:
            return 0
        
        # Calculate RMS
        rms = np.sqrt(np.mean(audio_array.astype(np.float64)**2))
        
        # Avoid log of zero
        if rms < 1:
            return 0
        
        # Convert to dB (reference: max int16 value)
        db = 20 * np.log10(rms / 32768.0) + 94 + self.calibration_offset
        return max(0, db)
    
    def detect_low_frequency(self, audio_data):
        """Detect low-frequency content (e.g., car rumble)"""
        audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float64)
        
        # Apply FFT
        fft = np.fft.rfft(audio_array)
        freqs = np.fft.rfftfreq(len(audio_array), 1/self.device_sample_rate)
        
        # Calculate energy in low frequency band (20-200 Hz)
        low_freq_mask = (freqs >= 20) & (freqs <= 200)
        low_freq_energy = np.sum(np.abs(fft[low_freq_mask])**2)
        
        # Calculate total energy
        total_energy = np.sum(np.abs(fft)**2)
        
        # If more than 40% of energy is in low frequencies, consider it low-frequency noise
        if total_energy > 0:
            return (low_freq_energy / total_energy) > 0.4
        return False
    
    def save_audio_segment(self, audio_data, timestamp):
        """Save audio segment as MP3 file"""
        try:
            # Create WAV file temporarily
            wav_filename = f"{RECORDINGS_DIR}/temp_{timestamp}.wav"
            wf = wave.open(wav_filename, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(self.p.get_sample_size(FORMAT))
            wf.setframerate(self.device_sample_rate)
            wf.writeframes(audio_data)
            wf.close()
            
            # Convert to MP3
            mp3_filename = f"{RECORDINGS_DIR}/{timestamp}.mp3"
            audio = AudioSegment.from_wav(wav_filename)
            audio.export(mp3_filename, format="mp3", bitrate=MP3_BITRATE)
            
            # Remove temporary WAV file
            os.remove(wav_filename)
            
            return mp3_filename
        except Exception as e:
            self.error_occurred.emit(f"Error saving audio: {str(e)}")
            return None
    
    def log_event(self, timestamp, duration, peak_db, avg_db, filename, video_filename, low_freq):
        """Log an event to the database"""
        try:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''INSERT INTO events 
                         (timestamp, duration, peak_db, avg_db, filename, video_filename, low_frequency)
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      (timestamp, duration, peak_db, avg_db, filename, video_filename, low_freq))
            conn.commit()
            conn.close()
            
            # Emit event detected signal
            self.event_detected.emit({
                'timestamp': timestamp,
                'duration': duration,
                'peak_db': peak_db,
                'avg_db': avg_db,
                'filename': filename,
                'video_filename': video_filename,
                'low_frequency': low_freq
            })
        except Exception as e:
            self.error_occurred.emit(f"Error logging event: {str(e)}")
    
    def start_recording(self):
        """Start recording audio"""
        if self.recording:
            return
        
        if not PYAUDIO_AVAILABLE:
            self.error_occurred.emit("PyAudio not available. Please install it to enable recording.")
            return
        
        try:
            if self.p is None:
                self.p = pyaudio.PyAudio()
            
            # Ensure we have detected the sample rate for this device
            if self.device_index is not None:
                self.device_sample_rate = self.detect_sample_rate(self.device_index)
            
            self.stream = self.p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=self.device_sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=CHUNK
            )
            
            self.recording = True
            self.current_segment = []
            self.segment_start_time = datetime.now()
            self.status_updated.emit(f"Recording started at {self.device_sample_rate} Hz")
            
            # Start recording thread
            self.record_thread = threading.Thread(target=self._record_loop)
            self.record_thread.daemon = True
            self.record_thread.start()
            
        except Exception as e:
            self.error_occurred.emit(f"Error starting recording: {str(e)}")
            self.recording = False
    
    def stop_recording(self):
        """Stop recording audio"""
        if not self.recording:
            return
        
        self.recording = False
        
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
            self.stream = None
        
        # Save any remaining segment
        if self.current_segment:
            timestamp = self.segment_start_time.strftime("%Y%m%d_%H%M%S")
            audio_data = b''.join(self.current_segment)
            self.save_audio_segment(audio_data, timestamp)
        
        # Finalize any ongoing event
        if self.event_in_progress:
            self._finalize_event()
        
        self.status_updated.emit("Recording stopped")
    
    def _record_loop(self):
        """Main recording loop (runs in separate thread)"""
        post_event_counter = 0
        
        while self.recording:
            try:
                # Read audio data
                data = self.stream.read(CHUNK, exception_on_overflow=False)
                
                # Calculate dB level
                db_level = self.calculate_db(data)
                rms = np.sqrt(np.mean(np.frombuffer(data, dtype=np.int16).astype(np.float64)**2))
                
                # Emit level update
                self.level_updated.emit(rms, db_level)
                
                # Add to current segment
                self.current_segment.append(data)
                
                # Maintain ring buffer for pre-event context
                self.audio_ring_buffer.append(data)
                if len(self.audio_ring_buffer) > self.max_ring_buffer_samples:
                    self.audio_ring_buffer.pop(0)
                
                # Check if we've recorded enough for a segment (using device sample rate)
                if len(self.current_segment) * CHUNK >= self.device_sample_rate * RECORD_SECONDS:
                    # Save segment
                    timestamp = self.segment_start_time.strftime("%Y%m%d_%H%M%S")
                    audio_data = b''.join(self.current_segment)
                    self.save_audio_segment(audio_data, timestamp)
                    
                    # Start new segment
                    self.current_segment = []
                    self.segment_start_time = datetime.now()
                
                # Event detection
                if db_level >= self.threshold_db:
                    if not self.event_in_progress:
                        # Start new event - include pre-event buffer
                        self.event_in_progress = True
                        self.event_start_time = datetime.now()
                        self.event_peak_db = db_level
                        # Include audio from ring buffer for context
                        self.event_samples = list(self.audio_ring_buffer) + [data]
                        
                        # Start video recording if enabled
                        if self.video_enabled:
                            timestamp = self.event_start_time.strftime("%Y%m%d_%H%M%S_%f")
                            self.start_video_recording(timestamp)
                    else:
                        # Continue event
                        self.event_peak_db = max(self.event_peak_db, db_level)
                        self.event_samples.append(data)
                        
                        # Write video frame if recording
                        if self.video_writer is not None:
                            self.write_video_frame()
                    # Reset post-event counter
                    post_event_counter = 0
                else:
                    if self.event_in_progress:
                        # Continue collecting audio for post-event buffer
                        
                        # Continue writing video frames during post-event buffer
                        if self.video_writer is not None:
                            self.write_video_frame()
                        post_event_counter += 1
                        self.event_samples.append(data)
                        
                        # Check if we've collected enough post-event samples
                        post_event_samples_needed = int(self.post_event_buffer_seconds * self.device_sample_rate / CHUNK)
                        if post_event_counter >= post_event_samples_needed:
                            # Event ended (with buffer)
                            self._finalize_event()
                            post_event_counter = 0
                
                
            except Exception as e:
                if self.recording:  # Only emit error if still supposed to be recording
                    self.error_occurred.emit(f"Recording error: {str(e)}")
                break
    
    def _finalize_event(self):
        """Finalize and log a detected event"""
        if not self.event_in_progress:
            return
        
        event_end_time = datetime.now()
        duration = (event_end_time - self.event_start_time).total_seconds()
        
        # Stop video recording if active
        video_filename = None
        if self.video_writer is not None:
            video_filename = self.stop_video_recording()
        
        # Only log events longer than 0.1 seconds
        if duration < 0.1:
            self.event_in_progress = False
            self.event_samples = []
            # Clean up video file if created
            if video_filename and os.path.exists(video_filename):
                try:
                    os.remove(video_filename)
                except:
                    pass
            return
        
        # Calculate average dB
        db_values = [self.calculate_db(sample) for sample in self.event_samples]
        avg_db = np.mean(db_values)
        
        # Detect low frequency
        event_audio = b''.join(self.event_samples)
        low_freq = self.detect_low_frequency(event_audio)
        
        # Save event audio
        timestamp = self.event_start_time.strftime("%Y%m%d_%H%M%S_%f")
        filename = self.save_audio_segment(event_audio, f"event_{timestamp}")
        
        # Log event
        if filename:
            self.log_event(
                self.event_start_time.strftime("%Y-%m-%d %H:%M:%S.%f"),
                duration,
                self.event_peak_db,
                avg_db,
                filename,
                video_filename,
                low_freq
            )
            
            # Emit notification for extreme events
            if self.event_peak_db >= self.threshold_db + 10:
                self.status_updated.emit(f"EXTREME NOISE DETECTED: {self.event_peak_db:.1f} dB")
        
        # Reset event tracking
        self.event_in_progress = False
        self.event_samples = []


class WaveformWidget(FigureCanvas):
    """Widget for displaying live audio waveform"""
    
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(8, 2))
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        
        self.ax.set_ylim(-32768, 32768)
        self.ax.set_xlim(0, CHUNK)
        self.ax.set_xlabel('Samples')
        self.ax.set_ylabel('Amplitude')
        self.ax.set_title('Live Waveform')
        self.ax.grid(True, alpha=0.3)
        
        self.line, = self.ax.plot([], [], 'b-', linewidth=0.5)
        self.fig.tight_layout()
        
    def update_waveform(self, audio_data):
        """Update waveform display with new audio data"""
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        x = np.arange(len(audio_array))
        self.line.set_data(x, audio_array)
        self.ax.set_xlim(0, len(audio_array))
        self.draw()


class DecibelMeter(QWidget):
    """Widget for displaying decibel level meter"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        
        self.label = QLabel("0.0 dB")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("font-size: 24pt; font-weight: bold;")
        
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(120)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setOrientation(Qt.Vertical)
        
        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        self.setLayout(layout)
        
    def update_level(self, db_level):
        """Update the dB meter display"""
        self.label.setText(f"{db_level:.1f} dB")
        self.progress.setValue(int(db_level))
        
        # Color code based on level
        if db_level < 50:
            color = "green"
        elif db_level < 70:
            color = "yellow"
        elif db_level < 90:
            color = "orange"
        else:
            color = "red"
        
        self.progress.setStyleSheet(f"""
            QProgressBar::chunk {{
                background-color: {color};
            }}
        """)


class EventLogTable(QTableWidget):
    """Table widget for displaying logged events"""
    
    play_requested = pyqtSignal(str)  # filename to play
    play_video_requested = pyqtSignal(str)  # video filename to play
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(7)
        self.setHorizontalHeaderLabels([
            'Timestamp', 'Duration (s)', 'Peak dB', 'Avg dB', 'Low Freq', 'Filename', 'Video'
        ])
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        
        # Connect double-click to play
        self.cellDoubleClicked.connect(self._on_double_click)
        
    def _on_double_click(self, row, col):
        """Handle double-click to play audio or video"""
        # If video column clicked and video exists, play video
        if col == 6:
            video_item = self.item(row, 6)
            if video_item and video_item.data(Qt.UserRole):
                video_filename = video_item.data(Qt.UserRole)
                self.play_video_requested.emit(video_filename)
                return
        
        # Otherwise play audio
        filename_item = self.item(row, 5)
        if filename_item:
            self.play_requested.emit(filename_item.text())
    
    def load_events(self, filter_min_db=None):
        """Load events from database"""
        try:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            
            if filter_min_db is not None:
                c.execute('''SELECT timestamp, duration, peak_db, avg_db, 
                             low_frequency, filename, video_filename 
                             FROM events 
                             WHERE peak_db >= ?
                             ORDER BY timestamp DESC''', (filter_min_db,))
            else:
                c.execute('''SELECT timestamp, duration, peak_db, avg_db,
                             low_frequency, filename, video_filename 
                             FROM events 
                             ORDER BY timestamp DESC''')
            
            rows = c.fetchall()
            conn.close()
            
            self.setRowCount(len(rows))
            for i, row in enumerate(rows):
                self.setItem(i, 0, QTableWidgetItem(row[0]))
                self.setItem(i, 1, QTableWidgetItem(f"{row[1]:.2f}"))
                self.setItem(i, 2, QTableWidgetItem(f"{row[2]:.1f}"))
                self.setItem(i, 3, QTableWidgetItem(f"{row[3]:.1f}"))
                self.setItem(i, 4, QTableWidgetItem("Yes" if row[4] else "No"))
                self.setItem(i, 5, QTableWidgetItem(row[5]))
                # Store video filename as item data for later retrieval
                if len(row) > 6 and row[6]:
                    video_item = QTableWidgetItem("📹 Yes")
                    video_item.setData(Qt.UserRole, row[6])  # Store video filename
                else:
                    video_item = QTableWidgetItem("No")
                self.setItem(i, 6, video_item)
            
            self.resizeColumnsToContents()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load events: {str(e)}")
    
    def export_to_csv(self, filename):
        """Export table data to CSV"""
        try:
            import csv
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                
                # Write header
                headers = [self.horizontalHeaderItem(i).text() 
                          for i in range(self.columnCount())]
                writer.writerow(headers)
                
                # Write data
                for row in range(self.rowCount()):
                    row_data = [self.item(row, col).text() 
                               for col in range(self.columnCount())]
                    writer.writerow(row_data)
            
            return True
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to export: {str(e)}")
            return False


class StatisticsWidget(QWidget):
    """Widget for displaying statistics"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QGridLayout()
        
        self.total_time_label = QLabel("Total Recording Time: 0:00:00")
        self.event_count_label = QLabel("Total Events: 0")
        self.avg_db_label = QLabel("Average Peak dB: 0.0")
        self.max_db_label = QLabel("Maximum Peak dB: 0.0")
        self.low_freq_count_label = QLabel("Low Frequency Events: 0")
        
        layout.addWidget(self.total_time_label, 0, 0)
        layout.addWidget(self.event_count_label, 1, 0)
        layout.addWidget(self.avg_db_label, 2, 0)
        layout.addWidget(self.max_db_label, 3, 0)
        layout.addWidget(self.low_freq_count_label, 4, 0)
        
        self.setLayout(layout)
        
    def update_statistics(self):
        """Update statistics from database"""
        try:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            
            # Get event count
            c.execute('SELECT COUNT(*) FROM events')
            event_count = c.fetchone()[0]
            
            # Get average and max peak dB
            c.execute('SELECT AVG(peak_db), MAX(peak_db) FROM events')
            result = c.fetchone()
            avg_db = result[0] if result[0] else 0
            max_db = result[1] if result[1] else 0
            
            # Get total duration
            c.execute('SELECT SUM(duration) FROM events')
            total_duration = c.fetchone()[0] if c.fetchone()[0] else 0
            
            # Get low frequency count
            c.execute('SELECT COUNT(*) FROM events WHERE low_frequency = 1')
            low_freq_count = c.fetchone()[0]
            
            conn.close()
            
            # Update labels
            hours = int(total_duration // 3600)
            minutes = int((total_duration % 3600) // 60)
            seconds = int(total_duration % 60)
            
            self.total_time_label.setText(f"Total Recording Time: {hours}:{minutes:02d}:{seconds:02d}")
            self.event_count_label.setText(f"Total Events: {event_count}")
            self.avg_db_label.setText(f"Average Peak dB: {avg_db:.1f}")
            self.max_db_label.setText(f"Maximum Peak dB: {max_db:.1f}")
            self.low_freq_count_label.setText(f"Low Frequency Events: {low_freq_count}")
            
        except Exception as e:
            pass


class CameraPreviewWidget(QLabel):
    """Widget for displaying live camera preview"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.camera_index = 0
        self.capture = None
        self.timer = None
        self.current_frame = None  # Store current frame for video recording
        self.setMinimumSize(VIDEO_WIDTH, VIDEO_HEIGHT)
        self.setMaximumSize(VIDEO_WIDTH, VIDEO_HEIGHT)
        self.setScaledContents(True)
        self.setStyleSheet("QLabel { background-color: black; border: 2px solid gray; }")
        self.setText("No Camera")
        self.setAlignment(Qt.AlignCenter)
    
    def get_current_frame(self):
        """Get the current camera frame for video recording (BGR format)"""
        return self.current_frame
    
    def start_preview(self, camera_index=0):
        """Start camera preview"""
        if not CV2_AVAILABLE:
            self.setText("OpenCV not available")
            return
        
        self.camera_index = camera_index
        
        # Stop existing capture if any
        self.stop_preview()
        
        # Start new capture
        try:
            self.capture = cv2.VideoCapture(camera_index)
            if not self.capture.isOpened():
                self.setText(f"Cannot open camera {camera_index}")
                return
            
            # Set camera properties
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, VIDEO_WIDTH)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, VIDEO_HEIGHT)
            
            # Start timer to update frames
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_frame)
            self.timer.start(int(1000 / VIDEO_FPS))  # Update at VIDEO_FPS
        except Exception as e:
            self.setText(f"Error: {str(e)}")
    
    def update_frame(self):
        """Update the displayed frame"""
        if self.capture is None or not self.capture.isOpened():
            return
        
        try:
            ret, frame = self.capture.read()
            if ret:
                # Store current frame for video recording (BGR format)
                self.current_frame = frame.copy()
                
                # Convert BGR to RGB for display
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Convert to QImage
                h, w, ch = frame_rgb.shape
                bytes_per_line = ch * w
                qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                
                # Display
                self.setPixmap(QPixmap.fromImage(qt_image))
        except Exception as e:
            self.setText(f"Error: {str(e)}")
    
    def stop_preview(self):
        """Stop camera preview"""
        if self.timer is not None:
            self.timer.stop()
            self.timer = None
        
        if self.capture is not None:
            self.capture.release()
            self.capture = None
        
        self.current_frame = None
        self.setText("No Camera")
    
    def closeEvent(self, event):
        """Clean up when widget is closed"""
        self.stop_preview()
        super().closeEvent(event)


class SoundMonitorApp(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.audio_processor = AudioProcessor()
        self.last_audio_data = None
        self.extreme_event_notifications = []  # Track recent notifications
        
        # Connect signals
        self.audio_processor.level_updated.connect(self.on_level_updated)
        self.audio_processor.event_detected.connect(self.on_event_detected)
        self.audio_processor.status_updated.connect(self.on_status_updated)
        self.audio_processor.error_occurred.connect(self.on_error_occurred)
        
        self.init_ui()
        
        # Timer for updating waveform and statistics
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_displays)
        self.update_timer.start(100)  # Update every 100ms
        
    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("Sound Monitor - Noise Pollution Documentation Tool")
        self.setGeometry(100, 100, 1400, 900)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Notification panel for extreme events
        self.notification_panel = QLabel("")
        self.notification_panel.setStyleSheet(
            "background-color: #ffcccc; color: #cc0000; padding: 10px; "
            "font-weight: bold; font-size: 12pt; border: 2px solid #cc0000;"
        )
        self.notification_panel.setWordWrap(True)
        self.notification_panel.setAlignment(Qt.AlignCenter)
        self.notification_panel.hide()  # Hidden by default
        main_layout.addWidget(self.notification_panel)
        
        # Control panel
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)
        
        # Tab widget for different views
        tabs = QTabWidget()
        
        # Live monitoring tab
        live_tab = self.create_live_tab()
        tabs.addTab(live_tab, "Live Monitoring")
        
        # Event log tab
        log_tab = self.create_log_tab()
        tabs.addTab(log_tab, "Event Log")
        
        # Analytics tab (NEW)
        analytics_tab = self.create_analytics_tab()
        tabs.addTab(analytics_tab, "Analytics")
        
        # Statistics tab
        stats_tab = self.create_statistics_tab()
        tabs.addTab(stats_tab, "Statistics")
        
        # Settings tab
        settings_tab = self.create_settings_tab()
        tabs.addTab(settings_tab, "Settings")
        
        main_layout.addWidget(tabs)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
    def create_control_panel(self):
        """Create the main control panel"""
        panel = QGroupBox("Controls")
        layout = QHBoxLayout()
        
        # Device selection
        layout.addWidget(QLabel("Microphone:"))
        self.device_combo = QComboBox()
        devices = self.audio_processor.get_audio_devices()
        for idx, name in devices:
            self.device_combo.addItem(name, idx)
        self.device_combo.currentIndexChanged.connect(self.on_device_changed)
        if devices:
            self.audio_processor.set_device(devices[0][0])
        layout.addWidget(self.device_combo)
        
        # Start/Stop button
        self.record_button = QPushButton("Start Recording")
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setStyleSheet("QPushButton { background-color: green; color: white; font-weight: bold; padding: 10px; }")
        layout.addWidget(self.record_button)
        
        # Threshold slider
        layout.addWidget(QLabel("Threshold:"))
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setMinimum(40)
        self.threshold_slider.setMaximum(120)
        self.threshold_slider.setValue(80)
        self.threshold_slider.setTickPosition(QSlider.TicksBelow)
        self.threshold_slider.setTickInterval(10)
        self.threshold_slider.valueChanged.connect(self.on_threshold_changed)
        layout.addWidget(self.threshold_slider)
        
        self.threshold_label = QLabel("80 dB")
        layout.addWidget(self.threshold_label)
        
        panel.setLayout(layout)
        return panel
    
    def create_live_tab(self):
        """Create the live monitoring tab"""
        widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Top row: Audio monitoring
        audio_layout = QHBoxLayout()
        
        # Left side: waveform
        waveform_group = QGroupBox("Live Waveform")
        waveform_layout = QVBoxLayout()
        self.waveform = WaveformWidget()
        waveform_layout.addWidget(self.waveform)
        waveform_group.setLayout(waveform_layout)
        audio_layout.addWidget(waveform_group, stretch=3)
        
        # Right side: dB meter
        meter_group = QGroupBox("Sound Level")
        meter_layout = QVBoxLayout()
        self.db_meter = DecibelMeter()
        meter_layout.addWidget(self.db_meter)
        meter_group.setLayout(meter_layout)
        audio_layout.addWidget(meter_group, stretch=1)
        
        main_layout.addLayout(audio_layout, stretch=2)
        
        # Bottom row: Camera preview (if available)
        if CV2_AVAILABLE:
            camera_group = QGroupBox("📹 Camera Preview")
            camera_layout = QVBoxLayout()
            self.camera_preview = CameraPreviewWidget()
            camera_layout.addWidget(self.camera_preview)
            
            # Connect camera preview to audio processor for video recording
            self.audio_processor.set_camera_widget(self.camera_preview)
            
            camera_info = QLabel("<i>Enable video recording in Settings tab</i>")
            camera_info.setAlignment(Qt.AlignCenter)
            camera_layout.addWidget(camera_info)
            
            camera_group.setLayout(camera_layout)
            main_layout.addWidget(camera_group, stretch=1)
        
        widget.setLayout(main_layout)
        return widget
    
    def create_log_tab(self):
        """Create the event log tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter by minimum dB:"))
        self.filter_spinbox = QSpinBox()
        self.filter_spinbox.setMinimum(0)
        self.filter_spinbox.setMaximum(120)
        self.filter_spinbox.setValue(0)
        filter_layout.addWidget(self.filter_spinbox)
        
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_event_log)
        filter_layout.addWidget(refresh_button)
        
        export_button = QPushButton("Export to CSV")
        export_button.clicked.connect(self.export_events)
        filter_layout.addWidget(export_button)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Event table
        self.event_table = EventLogTable()
        self.event_table.play_requested.connect(self.play_audio)
        self.event_table.play_video_requested.connect(self.play_video)
        layout.addWidget(self.event_table)
        
        # Load initial events
        self.event_table.load_events()
        
        widget.setLayout(layout)
        return widget
    
    def create_analytics_tab(self):
        """Create the analytics tab with graphs and visualizations"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Refresh button at top
        refresh_layout = QHBoxLayout()
        refresh_button = QPushButton("Refresh Charts")
        refresh_button.clicked.connect(self.update_analytics)
        refresh_layout.addWidget(refresh_button)
        refresh_layout.addStretch()
        layout.addLayout(refresh_layout)
        
        # Create matplotlib figure with subplots
        from matplotlib.figure import Figure
        self.analytics_figure = Figure(figsize=(12, 8))
        self.analytics_canvas = FigureCanvas(self.analytics_figure)
        layout.addWidget(self.analytics_canvas)
        
        # Initial update
        self.update_analytics()
        
        widget.setLayout(layout)
        return widget
    
    def update_analytics(self):
        """Update analytics charts with event data"""
        try:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            
            # Get all events
            c.execute('''SELECT timestamp, duration, peak_db, avg_db, low_frequency 
                         FROM events 
                         ORDER BY timestamp''')
            events = c.fetchall()
            conn.close()
            
            if not events:
                # No data yet
                self.analytics_figure.clear()
                ax = self.analytics_figure.add_subplot(111)
                ax.text(0.5, 0.5, 'No event data available yet.\nStart recording to see analytics.',
                       ha='center', va='center', fontsize=14)
                self.analytics_canvas.draw()
                return
            
            # Parse data
            from datetime import datetime as dt
            timestamps = [dt.strptime(e[0], "%Y-%m-%d %H:%M:%S.%f") for e in events]
            durations = [float(e[1]) for e in events]
            peak_dbs = [float(e[2]) for e in events]
            avg_dbs = [float(e[3]) for e in events]
            
            # Convert low_frequency to int (handle int, bool, bytes, and None types from SQLite)
            def safe_bool_to_int(value):
                """Safely convert various boolean representations to int"""
                if value is None:
                    return 0
                if isinstance(value, bytes):
                    # Bytes like b'\x00' (False) or b'\x01' (True)
                    return 1 if value and value != b'\x00' else 0
                if isinstance(value, (int, bool)):
                    return int(value)
                # String representation
                return 1 if str(value).lower() in ('1', 'true', 'yes') else 0
            
            low_freq = [safe_bool_to_int(e[4]) for e in events]
            
            # Clear previous plots
            self.analytics_figure.clear()
            
            # Create 4 subplots
            ax1 = self.analytics_figure.add_subplot(2, 2, 1)
            ax2 = self.analytics_figure.add_subplot(2, 2, 2)
            ax3 = self.analytics_figure.add_subplot(2, 2, 3)
            ax4 = self.analytics_figure.add_subplot(2, 2, 4)
            
            # Plot 1: Events over time (scatter with size = duration)
            # Format x-axis with AM/PM time
            import matplotlib.dates as mdates
            ax1.scatter(timestamps, peak_dbs, s=[d*20 for d in durations], alpha=0.6, c=peak_dbs, cmap='YlOrRd')
            ax1.set_xlabel('Time (EST/EDT)')
            ax1.set_ylabel('Peak dB')
            ax1.set_title('Noise Events Over Time\n(bubble size = duration)')
            ax1.grid(True, alpha=0.3)
            # Format x-axis to show dates and times in 12-hour format
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d\n%I:%M %p'))
            ax1.tick_params(axis='x', rotation=45)
            
            # Plot 2: dB Level Distribution (histogram)
            ax2.hist(peak_dbs, bins=20, color='orange', alpha=0.7, edgecolor='black')
            ax2.set_xlabel('Peak dB Level')
            ax2.set_ylabel('Number of Events')
            ax2.set_title('Distribution of Noise Levels')
            ax2.grid(True, alpha=0.3, axis='y')
            ax2.axvline(np.mean(peak_dbs), color='red', linestyle='--', linewidth=2, label=f'Mean: {np.mean(peak_dbs):.1f} dB')
            ax2.legend()
            
            # Plot 3: Events by hour of day (12-hour format with AM/PM)
            hours = [t.hour for t in timestamps]
            hour_counts = [hours.count(h) for h in range(24)]
            
            # Create 12-hour labels with AM/PM
            hour_labels = []
            for h in range(24):
                if h == 0:
                    hour_labels.append('12 AM')
                elif h < 12:
                    hour_labels.append(f'{h} AM')
                elif h == 12:
                    hour_labels.append('12 PM')
                else:
                    hour_labels.append(f'{h-12} PM')
            
            ax3.bar(range(24), hour_counts, color='steelblue', alpha=0.7, edgecolor='black')
            ax3.set_xlabel('Hour of Day (EST/EDT)')
            ax3.set_ylabel('Number of Events')
            ax3.set_title('Noise Events by Hour of Day')
            # Set x-ticks to show every 2 hours in 12-hour format
            ax3.set_xticks(range(0, 24, 2))
            ax3.set_xticklabels([hour_labels[i] for i in range(0, 24, 2)], rotation=45, ha='right')
            ax3.grid(True, alpha=0.3, axis='y')
            
            # Plot 4: Low frequency vs Normal frequency
            low_freq_count = sum(low_freq)
            normal_freq_count = len(low_freq) - low_freq_count
            ax4.pie([normal_freq_count, low_freq_count], 
                   labels=['Normal Frequency', 'Low Frequency\n(Vehicle Rumble)'],
                   autopct='%1.1f%%',
                   colors=['lightblue', 'darkred'],
                   startangle=90)
            ax4.set_title('Frequency Distribution of Events')
            
            self.analytics_figure.tight_layout()
            self.analytics_canvas.draw()
            
        except Exception as e:
            # Error handling
            self.analytics_figure.clear()
            ax = self.analytics_figure.add_subplot(111)
            ax.text(0.5, 0.5, f'Error loading analytics:\n{str(e)}',
                   ha='center', va='center', fontsize=12, color='red')
            self.analytics_canvas.draw()
    
    def create_statistics_tab(self):
        """Create the statistics tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        self.statistics_widget = StatisticsWidget()
        layout.addWidget(self.statistics_widget)
        
        refresh_button = QPushButton("Refresh Statistics")
        refresh_button.clicked.connect(self.statistics_widget.update_statistics)
        layout.addWidget(refresh_button)
        
        layout.addStretch()
        
        # Initial update
        self.statistics_widget.update_statistics()
        
        widget.setLayout(layout)
        return widget
    
    def create_settings_tab(self):
        """Create the settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Calibration group - Enhanced
        calibration_group = QGroupBox("🎤 Microphone Calibration")
        cal_layout = QVBoxLayout()
        
        cal_info = QLabel(
            "<b>Calibrate your microphone for accurate dB readings:</b><br>"
            "1. Use a calibrated sound level meter as reference<br>"
            "2. Make a constant noise (clap, music, etc.)<br>"
            "3. Compare the reading on this app with your meter<br>"
            "4. Adjust the offset until they match<br>"
            "<br><i>Example: If app shows 75 dB but meter shows 80 dB, set offset to +5.0</i>"
        )
        cal_info.setWordWrap(True)
        cal_layout.addWidget(cal_info)
        
        # Current reading display
        self.current_db_label = QLabel("Current Reading: -- dB")
        self.current_db_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: blue;")
        cal_layout.addWidget(self.current_db_label)
        
        # Calibration offset control
        cal_control_layout = QHBoxLayout()
        cal_control_layout.addWidget(QLabel("Calibration Offset (dB):"))
        self.calibration_spinbox = QDoubleSpinBox()
        self.calibration_spinbox.setMinimum(-50)
        self.calibration_spinbox.setMaximum(50)
        self.calibration_spinbox.setValue(0)
        self.calibration_spinbox.setSingleStep(0.5)
        self.calibration_spinbox.valueChanged.connect(self.on_calibration_changed)
        self.calibration_spinbox.setStyleSheet("font-size: 12pt; font-weight: bold;")
        cal_control_layout.addWidget(self.calibration_spinbox)
        
        # Quick adjustment buttons
        quick_minus_5 = QPushButton("-5")
        quick_minus_5.clicked.connect(lambda: self.adjust_calibration(-5))
        cal_control_layout.addWidget(quick_minus_5)
        
        quick_minus_1 = QPushButton("-1")
        quick_minus_1.clicked.connect(lambda: self.adjust_calibration(-1))
        cal_control_layout.addWidget(quick_minus_1)
        
        quick_plus_1 = QPushButton("+1")
        quick_plus_1.clicked.connect(lambda: self.adjust_calibration(+1))
        cal_control_layout.addWidget(quick_plus_1)
        
        quick_plus_5 = QPushButton("+5")
        quick_plus_5.clicked.connect(lambda: self.adjust_calibration(+5))
        cal_control_layout.addWidget(quick_plus_5)
        
        reset_cal = QPushButton("Reset")
        reset_cal.clicked.connect(lambda: self.calibration_spinbox.setValue(0))
        cal_control_layout.addWidget(reset_cal)
        
        cal_control_layout.addStretch()
        cal_layout.addLayout(cal_control_layout)
        
        # Calibrated reading display
        self.calibrated_db_label = QLabel("Calibrated Reading: -- dB")
        self.calibrated_db_label.setStyleSheet("font-size: 18pt; font-weight: bold; color: green;")
        cal_layout.addWidget(self.calibrated_db_label)
        
        calibration_group.setLayout(cal_layout)
        layout.addWidget(calibration_group)
        
        # Device info
        device_group = QGroupBox("Audio Device Information")
        device_layout = QVBoxLayout()
        
        self.device_info_label = QLabel("Select a device from the dropdown above")
        self.device_info_label.setWordWrap(True)
        device_layout.addWidget(self.device_info_label)
        
        device_group.setLayout(device_layout)
        layout.addWidget(device_group)
        
        # Camera settings (if available)
        if CV2_AVAILABLE:
            camera_group = QGroupBox("📹 Video Recording Settings")
            camera_layout = QVBoxLayout()
            
            # Enable/disable video recording
            self.video_enabled_checkbox = QCheckBox("Enable Video Recording on Loud Events")
            self.video_enabled_checkbox.setChecked(False)
            self.video_enabled_checkbox.stateChanged.connect(self.on_video_enabled_changed)
            camera_layout.addWidget(self.video_enabled_checkbox)
            
            # Camera selection
            camera_select_layout = QHBoxLayout()
            camera_select_layout.addWidget(QLabel("Camera:"))
            self.camera_combo = QComboBox()
            cameras = self.audio_processor.get_camera_devices()
            for idx, name in cameras:
                self.camera_combo.addItem(name, idx)
            self.camera_combo.currentIndexChanged.connect(self.on_camera_changed)
            if cameras:
                self.audio_processor.set_camera(cameras[0][0])
            camera_select_layout.addWidget(self.camera_combo)
            camera_select_layout.addStretch()
            camera_layout.addLayout(camera_select_layout)
            
            # Info about video settings
            video_info = QLabel(
                f"<i>Video: {VIDEO_WIDTH}x{VIDEO_HEIGHT} @ {VIDEO_FPS} FPS<br>"
                "Videos only recorded during loud events to save storage<br>"
                "Approx. 5-10 MB per minute of event video</i>"
            )
            video_info.setWordWrap(True)
            camera_layout.addWidget(video_info)
            
            camera_group.setLayout(camera_layout)
            layout.addWidget(camera_group)
        
        # Storage info
        storage_group = QGroupBox("Storage Information")
        storage_layout = QVBoxLayout()
        
        self.storage_label = QLabel("Calculating storage usage...")
        storage_layout.addWidget(self.storage_label)
        
        storage_group.setLayout(storage_layout)
        layout.addWidget(storage_group)
        
        # System monitoring
        system_group = QGroupBox("System Status")
        system_layout = QVBoxLayout()
        
        self.system_status_text = QTextEdit()
        self.system_status_text.setReadOnly(True)
        self.system_status_text.setMaximumHeight(100)
        system_layout.addWidget(self.system_status_text)
        
        system_group.setLayout(system_layout)
        layout.addWidget(system_group)
        
        layout.addStretch()
        
        # Update storage info
        self.update_storage_info()
        self.update_system_status()
        
        widget.setLayout(layout)
        return widget
    
    def on_device_changed(self, index):
        """Handle device selection change"""
        device_index = self.device_combo.currentData()
        self.audio_processor.set_device(device_index)
        
        # Update device info display
        if PYAUDIO_AVAILABLE and device_index is not None:
            try:
                if self.audio_processor.p is None:
                    self.audio_processor.p = pyaudio.PyAudio()
                
                device_info = self.audio_processor.p.get_device_info_by_index(device_index)
                info_text = f"<b>Device:</b> {device_info['name']}<br>"
                info_text += f"<b>Sample Rate:</b> {self.audio_processor.device_sample_rate} Hz<br>"
                info_text += f"<b>Max Input Channels:</b> {device_info['maxInputChannels']}<br>"
                info_text += f"<b>Default Sample Rate:</b> {int(device_info['defaultSampleRate'])} Hz<br>"
                
                self.device_info_label.setText(info_text)
            except Exception as e:
                self.device_info_label.setText(f"Could not get device info: {str(e)}")
    
    def toggle_recording(self):
        """Toggle recording on/off"""
        if not self.audio_processor.recording:
            self.audio_processor.start_recording()
            self.record_button.setText("Stop Recording")
            self.record_button.setStyleSheet("QPushButton { background-color: red; color: white; font-weight: bold; padding: 10px; }")
        else:
            self.audio_processor.stop_recording()
            self.record_button.setText("Start Recording")
            self.record_button.setStyleSheet("QPushButton { background-color: green; color: white; font-weight: bold; padding: 10px; }")
    
    def on_threshold_changed(self, value):
        """Handle threshold slider change"""
        self.audio_processor.set_threshold(value)
        self.threshold_label.setText(f"{value} dB")
    
    def on_calibration_changed(self, value):
        """Handle calibration offset change"""
        self.audio_processor.set_calibration(value)
    
    def on_camera_changed(self, index):
        """Handle camera selection change"""
        if not CV2_AVAILABLE:
            return
        
        camera_index = self.camera_combo.currentData()
        self.audio_processor.set_camera(camera_index)
        
        # Update camera preview if exists
        if hasattr(self, 'camera_preview'):
            self.camera_preview.start_preview(camera_index)
    
    def on_video_enabled_changed(self, state):
        """Handle video enabled checkbox change"""
        enabled = (state == Qt.Checked)
        self.audio_processor.set_video_enabled(enabled)
        
        # Start/stop camera preview based on state
        if hasattr(self, 'camera_preview'):
            if enabled:
                camera_index = self.camera_combo.currentData() if hasattr(self, 'camera_combo') else 0
                self.camera_preview.start_preview(camera_index)
            else:
                self.camera_preview.stop_preview()
    
    def on_level_updated(self, rms, db_level):
        """Handle audio level update"""
        self.db_meter.update_level(db_level)
        
        # Update calibration display in settings tab
        raw_db = db_level - self.audio_processor.calibration_offset
        self.current_db_label.setText(f"Current Reading (raw): {raw_db:.1f} dB")
        self.calibrated_db_label.setText(f"Calibrated Reading: {db_level:.1f} dB")
    
    def adjust_calibration(self, delta):
        """Adjust calibration by a specific amount"""
        current = self.calibration_spinbox.value()
        self.calibration_spinbox.setValue(current + delta)
    
    def on_event_detected(self, event_data):
        """Handle event detection"""
        # Refresh event log
        self.refresh_event_log()
        
        # Update statistics
        self.statistics_widget.update_statistics()
        
        # Update analytics chart
        self.update_analytics()
        
        # Show notification for extreme events (in panel, not popup)
        if event_data['peak_db'] >= self.audio_processor.threshold_db + 10:
            # Add to notification list
            timestamp = event_data['timestamp']
            self.extreme_event_notifications.append({
                'time': timestamp,
                'db': event_data['peak_db'],
                'duration': event_data['duration']
            })
            
            # Keep only last 5 notifications
            if len(self.extreme_event_notifications) > 5:
                self.extreme_event_notifications.pop(0)
            
            # Update notification panel
            notification_text = "⚠️ EXTREME NOISE ALERTS:\n"
            for notif in reversed(self.extreme_event_notifications):
                notification_text += f"🔊 {notif['db']:.1f} dB at {notif['time']} ({notif['duration']:.1f}s)\n"
            
            self.notification_panel.setText(notification_text.strip())
            self.notification_panel.show()
            
            # Auto-hide after 30 seconds
            QTimer.singleShot(30000, self.hide_notification_panel)
    
    def hide_notification_panel(self):
        """Hide the notification panel"""
        if len(self.extreme_event_notifications) > 0:
            # If there are still notifications, update the panel but make it less prominent
            notification_text = f"⚠️ Recent extreme events: {len(self.extreme_event_notifications)} (Last: {self.extreme_event_notifications[-1]['db']:.1f} dB)"
            self.notification_panel.setText(notification_text)
            self.notification_panel.setStyleSheet(
                "background-color: #fff3cd; color: #856404; padding: 5px; "
                "font-weight: normal; font-size: 10pt; border: 1px solid #ffc107;"
            )
        else:
            self.notification_panel.hide()
    
    def on_status_updated(self, message):
        """Handle status update"""
        self.statusBar().showMessage(message)
    
    def on_error_occurred(self, error_message):
        """Handle error"""
        QMessageBox.warning(self, "Error", error_message)
        self.statusBar().showMessage(f"Error: {error_message}")
    
    def update_displays(self):
        """Update displays periodically"""
        # Store last audio data for waveform updates
        if self.audio_processor.recording and self.audio_processor.current_segment:
            if self.audio_processor.current_segment:
                self.last_audio_data = self.audio_processor.current_segment[-1]
                self.waveform.update_waveform(self.last_audio_data)
    
    def refresh_event_log(self):
        """Refresh the event log table"""
        min_db = self.filter_spinbox.value()
        if min_db > 0:
            self.event_table.load_events(filter_min_db=min_db)
        else:
            self.event_table.load_events()
    
    def export_events(self):
        """Export events to CSV"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Events",
            f"sound_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        
        if filename:
            if self.event_table.export_to_csv(filename):
                QMessageBox.information(self, "Success", f"Events exported to {filename}")
    
    def play_audio(self, filename):
        """Play audio file"""
        try:
            import subprocess
            import platform
            
            # Use system player to play audio
            system = platform.system()
            if system == 'Darwin':  # macOS
                subprocess.Popen(['afplay', filename])
            elif system == 'Linux':
                subprocess.Popen(['mpg123', filename])
            elif system == 'Windows':
                os.startfile(filename)
            else:
                QMessageBox.warning(self, "Error", "Audio playback not supported on this platform")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to play audio: {str(e)}")
    
    def play_video(self, video_filename):
        """Play video file"""
        try:
            import subprocess
            import platform
            
            if not os.path.exists(video_filename):
                QMessageBox.warning(self, "Error", f"Video file not found: {video_filename}")
                return
            
            # Use system player to play video
            system = platform.system()
            if system == 'Darwin':  # macOS
                subprocess.Popen(['open', video_filename])
            elif system == 'Linux':
                # Try common Linux video players
                for player in ['vlc', 'mpv', 'ffplay', 'mplayer']:
                    try:
                        subprocess.Popen([player, video_filename])
                        return
                    except FileNotFoundError:
                        continue
                QMessageBox.warning(self, "Error", "No video player found. Please install vlc, mpv, or ffplay.")
            elif system == 'Windows':
                os.startfile(video_filename)
            else:
                QMessageBox.warning(self, "Error", "Video playback not supported on this platform")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to play video: {str(e)}")
    
    def update_storage_info(self):
        """Update storage information"""
        try:
            import shutil
            total, used, free = shutil.disk_usage(RECORDINGS_DIR)
            
            # Calculate recording directory size
            recordings_size = 0
            for root, dirs, files in os.walk(RECORDINGS_DIR):
                recordings_size += sum(os.path.getsize(os.path.join(root, f)) for f in files)
            
            gb_total = total / (1024**3)
            gb_free = free / (1024**3)
            gb_used = recordings_size / (1024**3)
            
            info_text = f"Total disk space: {gb_total:.2f} GB\n"
            info_text += f"Free disk space: {gb_free:.2f} GB\n"
            info_text += f"Recordings size: {gb_used:.2f} GB\n"
            
            # Estimate recording capacity
            # Assuming 64kbps MP3, approximately 28.8 MB per hour
            hours_per_gb = 1024 / 28.8
            estimated_hours = gb_free * hours_per_gb
            estimated_days = estimated_hours / 24
            
            info_text += f"\nEstimated capacity: {estimated_days:.1f} days"
            
            self.storage_label.setText(info_text)
        except Exception as e:
            self.storage_label.setText(f"Error calculating storage: {str(e)}")
    
    def update_system_status(self):
        """Update system status"""
        try:
            import psutil
            
            # Battery info
            battery = psutil.sensors_battery()
            battery_info = "N/A (Desktop)"
            if battery:
                battery_info = f"{battery.percent}% ({'Charging' if battery.power_plugged else 'Battery'})"
            
            # CPU and memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            status_text = f"Battery: {battery_info}\n"
            status_text += f"CPU Usage: {cpu_percent}%\n"
            status_text += f"Memory Usage: {memory.percent}%"
            
            self.system_status_text.setText(status_text)
        except ImportError:
            self.system_status_text.setText("Install psutil for system monitoring:\npip install psutil")
        except Exception as e:
            self.system_status_text.setText(f"Error: {str(e)}")
    
    def closeEvent(self, event):
        """Handle application close"""
        if self.audio_processor.recording:
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "Recording is in progress. Stop recording and exit?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.audio_processor.stop_recording()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    
    # Check if PyAudio is available
    if not PYAUDIO_AVAILABLE:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("PyAudio Not Available")
        msg.setText("PyAudio library is not installed. Audio recording will not work.")
        msg.setInformativeText(
            "To enable audio recording, install PyAudio:\n\n"
            "Linux: sudo apt-get install python3-pyaudio portaudio19-dev\n"
            "macOS: brew install portaudio && pip install pyaudio\n"
            "Windows: pip install pyaudio\n\n"
            "You can still view the interface and test other features."
        )
        msg.exec_()
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = SoundMonitorApp()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
