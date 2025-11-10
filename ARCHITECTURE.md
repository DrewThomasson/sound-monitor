# Sound Monitor - Technical Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Sound Monitor Application                 │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   PyQt5 GUI │──│Audio Processor│──│   Database   │       │
│  │             │  │   (Thread)    │  │   (SQLite)   │       │
│  └─────────────┘  └──────────────┘  └──────────────┘       │
│         │                │                    │              │
│         │                │                    │              │
│  ┌──────▼─────┐  ┌──────▼────────┐  ┌───────▼──────┐      │
│  │Visualization│  │ Audio Capture │  │Event Logging │      │
│  │  Widgets   │  │   (PyAudio)   │  │  & Storage   │      │
│  └────────────┘  └───────────────┘  └──────────────┘      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. Main Application (SoundMonitorApp)
- **Role:** Primary GUI window and coordinator
- **Responsibilities:**
  - Initialize UI components
  - Manage user interactions
  - Coordinate between components
  - Handle application lifecycle

### 2. Audio Processor (AudioProcessor)
- **Role:** Audio capture, analysis, and event detection
- **Responsibilities:**
  - Record audio from microphone
  - Calculate decibel levels
  - Detect events above threshold
  - Save audio as MP3
  - Manage recording thread
- **Threading:** Runs in separate thread to prevent GUI blocking
- **Signals:** Emits Qt signals for UI updates

### 3. Database Layer
- **Technology:** SQLite
- **Schema:**
  ```sql
  events (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    duration REAL,
    peak_db REAL,
    avg_db REAL,
    filename TEXT,
    low_frequency BOOLEAN
  )
  ```
- **Operations:**
  - Insert events
  - Query events (filtered, sorted)
  - Export to CSV

### 4. GUI Components

#### 4.1 WaveformWidget
- **Technology:** Matplotlib
- **Purpose:** Real-time audio visualization
- **Update Rate:** ~10 Hz

#### 4.2 DecibelMeter
- **Technology:** Qt Widgets
- **Purpose:** Visual dB level indicator
- **Features:** Color-coded levels

#### 4.3 EventLogTable
- **Technology:** QTableWidget
- **Purpose:** Display event history
- **Features:**
  - Sortable columns
  - Filtering
  - Double-click playback

#### 4.4 StatisticsWidget
- **Technology:** Qt Widgets
- **Purpose:** Display aggregate data
- **Metrics:**
  - Total recording time
  - Event count
  - Average/peak dB
  - Low-frequency events

## Data Flow

### Recording Flow
```
Microphone → PyAudio → AudioProcessor → MP3 File
                            │
                            ├→ dB Calculation
                            │
                            ├→ Event Detection
                            │
                            └→ Database (if event detected)
```

### Display Flow
```
AudioProcessor → Qt Signals → GUI Widgets → User Display
     │
     ├→ level_updated → DecibelMeter
     ├→ level_updated → WaveformWidget
     ├→ event_detected → EventLogTable
     ├→ status_updated → StatusBar
     └→ error_occurred → MessageBox
```

### Event Detection Algorithm
```
1. Read audio chunk (1024 samples)
2. Calculate RMS level
3. Convert to dB (20 * log10(RMS/32768) + 94 + calibration)
4. If dB >= threshold:
   - Start/continue event
   - Track peak dB
   - Store audio samples
5. If dB < threshold and event in progress:
   - Finalize event
   - Save audio to MP3
   - Log to database
   - Emit event signal
```

### Low-Frequency Detection
```
1. Apply FFT to audio samples
2. Calculate frequency spectrum
3. Measure energy in 20-200 Hz band
4. If low-freq energy > 40% of total:
   - Mark as low-frequency event
```

## File Organization

```
sound-monitor/
├── Application Code
│   ├── sound_monitor.py      # Main application (1000+ lines)
│   ├── run.py                # Launcher with dependency checks
│   └── test_sound_monitor.py # Test suite
│
├── Documentation
│   ├── README.md             # Overview and features
│   ├── INSTALL.md            # Installation guide
│   ├── QUICKSTART.md         # Quick reference
│   ├── CONTRIBUTING.md       # Contribution guidelines
│   └── ARCHITECTURE.md       # This file
│
├── Configuration
│   ├── requirements.txt      # Python dependencies
│   ├── setup.py             # Installation script
│   └── .gitignore           # Git ignore rules
│
├── Examples
│   └── example_demo.py      # Demo with sample data
│
└── Runtime (generated)
    ├── recordings/           # MP3 audio files
    │   ├── YYYYMMDD_HHMMSS.mp3       # Regular segments
    │   └── event_YYYYMMDD_HHMMSS.mp3 # Detected events
    └── sound_events.db      # SQLite database
```

## Threading Model

### Main Thread
- Qt GUI event loop
- Widget updates
- User interactions

### Recording Thread
- Audio capture
- Signal processing
- Event detection
- File I/O (MP3 encoding)

### Communication
- Qt Signals/Slots (thread-safe)
- No shared mutable state
- All data passed through signals

## Performance Characteristics

### CPU Usage
- Idle: ~1-2% (GUI updates only)
- Recording: ~5-10% (audio processing)
- Peak: ~15-20% (MP3 encoding)

### Memory Usage
- Base: ~80-100 MB (Qt/matplotlib)
- Recording: +20-30 MB (audio buffers)
- Stable over long runs (no leaks)

### Disk I/O
- Continuous: ~28.8 MB/hour (64kbps MP3)
- Burst: ~1-5 MB per event
- Sequential writes (optimized)

### Storage Efficiency
- 1 hour: ~29 MB
- 1 day: ~691 MB
- 1 week: ~4.8 GB
- 70 GB: ~100 days

## Error Handling

### Audio Device Errors
```python
try:
    stream = pyaudio.open(...)
except Exception as e:
    emit error_occurred signal
    stop recording gracefully
    notify user
```

### File System Errors
```python
try:
    save_audio_segment(...)
except Exception as e:
    log error
    continue recording
    notify user
```

### Database Errors
```python
try:
    insert_event(...)
except Exception as e:
    log locally
    retry connection
    notify user
```

## Dependencies

### Required
- **PyQt5**: GUI framework
- **numpy**: Numerical computations
- **pyaudio**: Audio capture
- **pydub**: Audio format conversion
- **matplotlib**: Waveform visualization
- **scipy**: Signal processing (FFT)

### System Libraries
- **PortAudio**: Audio I/O (via PyAudio)
- **FFmpeg**: MP3 encoding (via pydub)

### Optional
- **psutil**: System monitoring

## Security Considerations

### Data Privacy
- All data stored locally
- No network transmission
- No telemetry or analytics

### File Permissions
- Recordings directory: user-only access
- Database: user-only access
- Configuration: user-only access

### Input Validation
- Device index: validated against available devices
- Threshold: constrained to 40-120 dB
- File paths: sanitized timestamps only

## Extensibility Points

### Adding New Audio Formats
```python
# In save_audio_segment()
if format == 'ogg':
    audio.export(filename, format="ogg", codec="libvorbis")
```

### Adding New Event Detectors
```python
# In AudioProcessor._record_loop()
if custom_detector.detect(audio_data):
    self._start_custom_event()
```

### Adding New Visualizations
```python
# Create new widget inheriting from QWidget
class SpectrogramWidget(QWidget):
    def update_spectrogram(self, audio_data):
        # Custom visualization logic
```

### Adding Export Formats
```python
# In EventLogTable
def export_to_json(self, filename):
    # JSON export logic
```

## Testing Strategy

### Unit Tests
- Database operations
- Audio processing functions
- Event detection algorithm

### Integration Tests
- GUI component interaction
- Signal/slot connections
- File I/O operations

### Manual Tests
- Audio device selection
- Recording continuity
- Event playback
- CSV export

## Future Enhancements

### Planned Features
1. Stereo recording support
2. Frequency band analysis
3. Machine learning classification
4. Cloud backup integration
5. Mobile companion app

### Performance Optimizations
1. Circular buffer for audio
2. Batch database inserts
3. Asynchronous file writes
4. GPU-accelerated FFT

### UI Improvements
1. Dark mode theme
2. Customizable layouts
3. Keyboard shortcuts
4. Drag-and-drop calibration

---

**Version:** 1.0.0  
**Last Updated:** November 2024  
**Maintainer:** Sound Monitor Team
