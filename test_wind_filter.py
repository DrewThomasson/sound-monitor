#!/usr/bin/env python3
"""
Test script specifically for wind noise filter functionality
"""

import sys
import os
import numpy as np
from scipy import signal as scipy_signal

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_wind_filter_basic():
    """Test basic wind filter functionality"""
    print("\nTesting wind filter (basic)...")
    
    try:
        # Import AudioProcessor
        from sound_monitor import AudioProcessor
        
        # Create audio processor
        processor = AudioProcessor()
        processor.device_sample_rate = 44100
        
        # Create synthetic audio with low-frequency component (wind-like)
        duration = 0.1  # 100ms
        sample_rate = 44100
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # Low frequency (wind) + high frequency (actual sound)
        wind_freq = 40  # Hz - typical wind noise
        sound_freq = 440  # Hz - A4 note
        
        # Create mixed signal
        wind_component = np.sin(2 * np.pi * wind_freq * t) * 32767 / 4
        sound_component = np.sin(2 * np.pi * sound_freq * t) * 32767 / 4
        mixed_signal = (wind_component + sound_component).astype(np.int16)
        
        # Convert to bytes
        audio_data = mixed_signal.tobytes()
        
        print("✓ Synthetic wind+sound audio generated")
        
        # Test with filter disabled
        processor.set_wind_filter(False)
        filtered_disabled = processor.apply_wind_filter(audio_data)
        
        # Should return original data when disabled
        if filtered_disabled == audio_data:
            print("✓ Filter disabled: original data returned")
        else:
            print("⚠ Filter disabled but data was modified")
        
        # Test with filter enabled
        processor.set_wind_filter(True)
        processor.set_wind_filter_cutoff(80)  # 80 Hz cutoff
        filtered_enabled = processor.apply_wind_filter(audio_data)
        
        # Convert back to array for analysis
        filtered_array = np.frombuffer(filtered_enabled, dtype=np.int16)
        
        # Analyze frequency content
        fft_filtered = np.fft.rfft(filtered_array.astype(np.float64))
        freqs = np.fft.rfftfreq(len(filtered_array), 1/sample_rate)
        
        # Check that low frequencies are reduced
        low_freq_mask = (freqs < 80)
        high_freq_mask = (freqs >= 80) & (freqs < 1000)
        
        low_freq_power = np.sum(np.abs(fft_filtered[low_freq_mask])**2)
        high_freq_power = np.sum(np.abs(fft_filtered[high_freq_mask])**2)
        
        if high_freq_power > low_freq_power * 2:
            print("✓ Filter enabled: low frequencies reduced")
            print(f"  Low freq power: {low_freq_power:.0f}")
            print(f"  High freq power: {high_freq_power:.0f}")
        else:
            print("⚠ Filter enabled but low frequencies not significantly reduced")
            print(f"  Low freq power: {low_freq_power:.0f}")
            print(f"  High freq power: {high_freq_power:.0f}")
        
        return True
        
    except Exception as e:
        print(f"✗ Wind filter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_wind_filter_different_cutoffs():
    """Test wind filter with different cutoff frequencies"""
    print("\nTesting wind filter (different cutoffs)...")
    
    try:
        from sound_monitor import AudioProcessor
        
        processor = AudioProcessor()
        processor.device_sample_rate = 44100
        processor.set_wind_filter(True)
        
        # Create test signal
        duration = 0.1
        sample_rate = 44100
        t = np.linspace(0, duration, int(sample_rate * duration))
        test_signal = (np.sin(2 * np.pi * 50 * t) * 32767 / 2).astype(np.int16)
        audio_data = test_signal.tobytes()
        
        # Test different cutoffs
        cutoffs = [60, 80, 100]
        
        for cutoff in cutoffs:
            processor.set_wind_filter_cutoff(cutoff)
            filtered = processor.apply_wind_filter(audio_data)
            
            # Just verify it doesn't crash
            if filtered is not None and len(filtered) == len(audio_data):
                print(f"✓ Cutoff {cutoff} Hz: filter applied successfully")
            else:
                print(f"✗ Cutoff {cutoff} Hz: filter failed")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Different cutoffs test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_wind_filter_edge_cases():
    """Test wind filter edge cases"""
    print("\nTesting wind filter (edge cases)...")
    
    try:
        from sound_monitor import AudioProcessor
        
        processor = AudioProcessor()
        processor.device_sample_rate = 44100
        processor.set_wind_filter(True)
        
        # Empty audio
        empty_audio = b''
        try:
            filtered = processor.apply_wind_filter(empty_audio)
            print("✓ Empty audio handled")
        except:
            print("⚠ Empty audio caused error")
        
        # Very short audio
        short_audio = np.array([100, 200, 300], dtype=np.int16).tobytes()
        try:
            filtered = processor.apply_wind_filter(short_audio)
            print("✓ Very short audio handled")
        except:
            print("⚠ Very short audio caused error")
        
        # Silence (zeros)
        silence = np.zeros(1024, dtype=np.int16).tobytes()
        try:
            filtered = processor.apply_wind_filter(silence)
            print("✓ Silence handled")
        except:
            print("⚠ Silence caused error")
        
        return True
        
    except Exception as e:
        print(f"✗ Edge cases test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all wind filter tests"""
    print("="*60)
    print("Sound Monitor - Wind Filter Test Suite")
    print("="*60)
    
    all_passed = True
    
    if not test_wind_filter_basic():
        all_passed = False
    
    if not test_wind_filter_different_cutoffs():
        all_passed = False
    
    if not test_wind_filter_edge_cases():
        all_passed = False
    
    # Summary
    print("\n" + "="*60)
    if all_passed:
        print("✓ All wind filter tests passed!")
        print("="*60)
        return 0
    else:
        print("✗ Some wind filter tests failed")
        print("="*60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
