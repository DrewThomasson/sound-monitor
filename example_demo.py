#!/usr/bin/env python3
"""
Example usage and demonstration of Sound Monitor features

This script demonstrates various features of the Sound Monitor application
without requiring actual audio hardware (for testing purposes).
"""

import sqlite3
import os
from datetime import datetime
from pathlib import Path


def create_sample_events():
    """Create sample event data for demonstration"""
    print("Creating sample event database...")
    
    # Create recordings directory
    Path("recordings").mkdir(exist_ok=True)
    
    # Initialize database
    conn = sqlite3.connect("sound_events.db")
    c = conn.cursor()
    
    # Create table
    c.execute('''CREATE TABLE IF NOT EXISTS events
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  duration REAL,
                  peak_db REAL,
                  avg_db REAL,
                  filename TEXT,
                  low_frequency BOOLEAN)''')
    
    # Sample events data
    sample_events = [
        ('2024-11-10 08:15:23', 2.3, 85.2, 82.1, 'recordings/event_20241110_081523.mp3', False),
        ('2024-11-10 08:47:15', 1.8, 78.5, 75.3, 'recordings/event_20241110_084715.mp3', True),
        ('2024-11-10 09:22:41', 3.1, 92.7, 88.4, 'recordings/event_20241110_092241.mp3', False),
        ('2024-11-10 10:05:33', 1.5, 73.2, 71.8, 'recordings/event_20241110_100533.mp3', True),
        ('2024-11-10 11:18:07', 4.2, 95.3, 91.2, 'recordings/event_20241110_111807.mp3', False),
        ('2024-11-10 12:33:29', 2.7, 88.9, 85.6, 'recordings/event_20241110_123329.mp3', True),
        ('2024-11-10 14:55:18', 1.9, 81.4, 78.9, 'recordings/event_20241110_145518.mp3', False),
        ('2024-11-10 16:42:55', 3.5, 97.1, 93.8, 'recordings/event_20241110_164255.mp3', False),
        ('2024-11-10 18:20:12', 2.1, 84.6, 82.3, 'recordings/event_20241110_182012.mp3', True),
        ('2024-11-10 20:08:47', 5.3, 99.2, 95.1, 'recordings/event_20241110_200847.mp3', False),
    ]
    
    # Insert sample events
    for event in sample_events:
        c.execute('''INSERT INTO events 
                     (timestamp, duration, peak_db, avg_db, filename, low_frequency)
                     VALUES (?, ?, ?, ?, ?, ?)''', event)
    
    conn.commit()
    conn.close()
    
    print(f"✓ Created {len(sample_events)} sample events")
    print("✓ Database ready at: sound_events.db")


def display_statistics():
    """Display statistics from the sample data"""
    print("\nSound Monitor Statistics:")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect("sound_events.db")
        c = conn.cursor()
        
        # Get event count
        c.execute('SELECT COUNT(*) FROM events')
        event_count = c.fetchone()[0]
        
        # Get average and max peak dB
        c.execute('SELECT AVG(peak_db), MAX(peak_db), MIN(peak_db) FROM events')
        result = c.fetchone()
        avg_db = result[0]
        max_db = result[1]
        min_db = result[2]
        
        # Get total duration
        c.execute('SELECT SUM(duration) FROM events')
        total_duration = c.fetchone()[0]
        
        # Get low frequency count
        c.execute('SELECT COUNT(*) FROM events WHERE low_frequency = 1')
        low_freq_count = c.fetchone()[0]
        
        # Get events by hour
        c.execute('''SELECT substr(timestamp, 12, 2) as hour, COUNT(*) as count
                     FROM events
                     GROUP BY hour
                     ORDER BY count DESC
                     LIMIT 3''')
        top_hours = c.fetchall()
        
        conn.close()
        
        # Display statistics
        print(f"Total Events Recorded: {event_count}")
        print(f"Total Event Duration: {total_duration:.1f} seconds")
        print(f"Average Peak dB: {avg_db:.1f} dB")
        print(f"Maximum Peak dB: {max_db:.1f} dB")
        print(f"Minimum Peak dB: {min_db:.1f} dB")
        print(f"Low Frequency Events: {low_freq_count} ({low_freq_count/event_count*100:.1f}%)")
        
        print("\nNoisiest Hours:")
        for hour, count in top_hours:
            print(f"  {hour}:00 - {count} events")
        
    except Exception as e:
        print(f"Error: {e}")
    
    print("=" * 60)


def export_sample_csv():
    """Export sample events to CSV"""
    import csv
    
    output_file = "sample_sound_events.csv"
    
    try:
        conn = sqlite3.connect("sound_events.db")
        c = conn.cursor()
        
        c.execute('''SELECT timestamp, duration, peak_db, avg_db, 
                     CASE WHEN low_frequency = 1 THEN 'Yes' ELSE 'No' END as low_freq,
                     filename 
                     FROM events 
                     ORDER BY peak_db DESC''')
        
        rows = c.fetchall()
        conn.close()
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'Duration (s)', 'Peak dB', 'Avg dB', 'Low Frequency', 'Filename'])
            writer.writerows(rows)
        
        print(f"\n✓ Exported events to: {output_file}")
        
    except Exception as e:
        print(f"Error exporting CSV: {e}")


def main():
    """Main demonstration function"""
    print("Sound Monitor - Feature Demonstration")
    print("=" * 60)
    print()
    
    # Create sample data
    create_sample_events()
    
    # Display statistics
    display_statistics()
    
    # Export to CSV
    export_sample_csv()
    
    print("\nTo start the Sound Monitor application, run:")
    print("  python3 sound_monitor.py")
    print("\nor:")
    print("  python3 run.py")
    print()
    print("The sample database is ready to view in the application!")
    print()


if __name__ == '__main__':
    main()
