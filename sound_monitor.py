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
    
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QSlider, QTableWidget, QTableWidgetItem,
    QTabWidget, QFileDialog, QMessageBox, QProgressBar, QGroupBox,
    QGridLayout, QSpinBox, QDoubleSpinBox, QCheckBox, QTextEdit
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QPalette, QColor
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
        self.threshold_db = 80
        self.calibration_offset = 0
        self.current_segment = []
        self.segment_start_time = None
        self.event_in_progress = False
        self.event_start_time = None
        self.event_peak_db = 0
        self.event_samples = []
        
        # Create recordings directory
        Path(RECORDINGS_DIR).mkdir(exist_ok=True)
        
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
                      low_frequency BOOLEAN)''')
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
    
    def set_device(self, device_index):
        """Set the input device"""
        self.device_index = device_index
        
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
        freqs = np.fft.rfftfreq(len(audio_array), 1/RATE)
        
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
            wf.setframerate(RATE)
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
    
    def log_event(self, timestamp, duration, peak_db, avg_db, filename, low_freq):
        """Log an event to the database"""
        try:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''INSERT INTO events 
                         (timestamp, duration, peak_db, avg_db, filename, low_frequency)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (timestamp, duration, peak_db, avg_db, filename, low_freq))
            conn.commit()
            conn.close()
            
            # Emit event detected signal
            self.event_detected.emit({
                'timestamp': timestamp,
                'duration': duration,
                'peak_db': peak_db,
                'avg_db': avg_db,
                'filename': filename,
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
            
            self.stream = self.p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=CHUNK
            )
            
            self.recording = True
            self.current_segment = []
            self.segment_start_time = datetime.now()
            self.status_updated.emit("Recording started")
            
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
                
                # Check if we've recorded enough for a segment
                if len(self.current_segment) * CHUNK >= RATE * RECORD_SECONDS:
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
                        # Start new event
                        self.event_in_progress = True
                        self.event_start_time = datetime.now()
                        self.event_peak_db = db_level
                        self.event_samples = [data]
                    else:
                        # Continue event
                        self.event_peak_db = max(self.event_peak_db, db_level)
                        self.event_samples.append(data)
                else:
                    if self.event_in_progress:
                        # Event ended
                        self._finalize_event()
                
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
        
        # Only log events longer than 0.1 seconds
        if duration < 0.1:
            self.event_in_progress = False
            self.event_samples = []
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
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels([
            'Timestamp', 'Duration (s)', 'Peak dB', 'Avg dB', 'Low Freq', 'Filename'
        ])
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        
        # Connect double-click to play
        self.cellDoubleClicked.connect(self._on_double_click)
        
    def _on_double_click(self, row, col):
        """Handle double-click to play audio"""
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
                             low_frequency, filename 
                             FROM events 
                             WHERE peak_db >= ?
                             ORDER BY timestamp DESC''', (filter_min_db,))
            else:
                c.execute('''SELECT timestamp, duration, peak_db, avg_db,
                             low_frequency, filename 
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


class SoundMonitorApp(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.audio_processor = AudioProcessor()
        self.last_audio_data = None
        
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
        layout = QHBoxLayout()
        
        # Left side: waveform
        waveform_group = QGroupBox("Live Waveform")
        waveform_layout = QVBoxLayout()
        self.waveform = WaveformWidget()
        waveform_layout.addWidget(self.waveform)
        waveform_group.setLayout(waveform_layout)
        layout.addWidget(waveform_group, stretch=3)
        
        # Right side: dB meter
        meter_group = QGroupBox("Sound Level")
        meter_layout = QVBoxLayout()
        self.db_meter = DecibelMeter()
        meter_layout.addWidget(self.db_meter)
        meter_group.setLayout(meter_layout)
        layout.addWidget(meter_group, stretch=1)
        
        widget.setLayout(layout)
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
        layout.addWidget(self.event_table)
        
        # Load initial events
        self.event_table.load_events()
        
        widget.setLayout(layout)
        return widget
    
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
        
        # Calibration group
        calibration_group = QGroupBox("Microphone Calibration")
        cal_layout = QVBoxLayout()
        
        cal_info = QLabel("Calibrate your microphone for accurate dB readings.\n"
                         "Use a calibrated sound level meter as reference.\n"
                         "Adjust the offset until readings match.")
        cal_layout.addWidget(cal_info)
        
        cal_control_layout = QHBoxLayout()
        cal_control_layout.addWidget(QLabel("Calibration Offset (dB):"))
        self.calibration_spinbox = QDoubleSpinBox()
        self.calibration_spinbox.setMinimum(-50)
        self.calibration_spinbox.setMaximum(50)
        self.calibration_spinbox.setValue(0)
        self.calibration_spinbox.setSingleStep(0.1)
        self.calibration_spinbox.valueChanged.connect(self.on_calibration_changed)
        cal_control_layout.addWidget(self.calibration_spinbox)
        cal_control_layout.addStretch()
        cal_layout.addLayout(cal_control_layout)
        
        calibration_group.setLayout(cal_layout)
        layout.addWidget(calibration_group)
        
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
    
    def on_level_updated(self, rms, db_level):
        """Handle audio level update"""
        self.db_meter.update_level(db_level)
    
    def on_event_detected(self, event_data):
        """Handle event detection"""
        # Refresh event log
        self.refresh_event_log()
        
        # Update statistics
        self.statistics_widget.update_statistics()
        
        # Show notification for extreme events
        if event_data['peak_db'] >= self.audio_processor.threshold_db + 10:
            QMessageBox.information(
                self, 
                "Extreme Noise Detected",
                f"Peak level: {event_data['peak_db']:.1f} dB\n"
                f"Duration: {event_data['duration']:.2f} seconds\n"
                f"Time: {event_data['timestamp']}"
            )
    
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
