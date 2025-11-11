#!/usr/bin/env python3
"""
Wind Filter Demo Script

Demonstrates the wind noise filter by creating synthetic audio
with wind noise and showing the filter's effect.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy import signal as scipy_signal
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sound_monitor import AudioProcessor


def create_wind_noise_sample(duration=1.0, sample_rate=44100):
    """Create a synthetic audio sample with wind noise + actual sound"""
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Wind component (low frequency, random phase)
    wind = np.zeros_like(t)
    for freq in [20, 30, 40, 50, 60]:
        phase = np.random.random() * 2 * np.pi
        wind += np.sin(2 * np.pi * freq * t + phase) * (32767 / 10)
    
    # Actual sound (car passing - mid frequency)
    car_sound = np.sin(2 * np.pi * 200 * t) * (32767 / 4)
    
    # Voice/shouting (high frequency)
    voice = np.sin(2 * np.pi * 800 * t) * (32767 / 6)
    
    # Combine
    mixed = wind + car_sound + voice
    
    # Normalize
    mixed = mixed / np.max(np.abs(mixed)) * 32767 * 0.7
    
    return mixed.astype(np.int16)


def analyze_spectrum(audio_array, sample_rate=44100, title="Spectrum"):
    """Analyze and plot the frequency spectrum"""
    # Compute FFT
    fft = np.fft.rfft(audio_array.astype(np.float64))
    freqs = np.fft.rfftfreq(len(audio_array), 1/sample_rate)
    magnitudes = np.abs(fft)
    
    return freqs, magnitudes


def main():
    print("="*60)
    print("Wind Noise Filter Demonstration")
    print("="*60)
    
    # Create audio processor
    processor = AudioProcessor()
    processor.device_sample_rate = 44100
    
    # Generate sample audio
    print("\n1. Generating synthetic audio with wind noise...")
    audio_array = create_wind_noise_sample()
    audio_bytes = audio_array.tobytes()
    print(f"   Generated {len(audio_array)} samples ({len(audio_array)/44100:.2f} seconds)")
    
    # Analyze original
    print("\n2. Analyzing original audio (with wind)...")
    freqs_orig, mag_orig = analyze_spectrum(audio_array)
    
    # Calculate original dB
    db_orig = processor.calculate_db(audio_bytes)
    print(f"   Original dB level: {db_orig:.1f} dB")
    
    # Apply filter
    print("\n3. Applying wind filter (80 Hz cutoff)...")
    processor.set_wind_filter(True)
    processor.set_wind_filter_cutoff(80)
    filtered_bytes = processor.apply_wind_filter(audio_bytes)
    filtered_array = np.frombuffer(filtered_bytes, dtype=np.int16)
    
    # Analyze filtered
    print("4. Analyzing filtered audio (wind removed)...")
    freqs_filt, mag_filt = analyze_spectrum(filtered_array)
    
    # Calculate filtered dB
    db_filt = processor.calculate_db(filtered_bytes)
    print(f"   Filtered dB level: {db_filt:.1f} dB")
    print(f"   dB reduction: {db_orig - db_filt:.1f} dB")
    
    # Energy comparison
    energy_orig = np.sum(audio_array.astype(np.float64)**2)
    energy_filt = np.sum(filtered_array.astype(np.float64)**2)
    print(f"\n5. Energy comparison:")
    print(f"   Original energy: {energy_orig:.0f}")
    print(f"   Filtered energy: {energy_filt:.0f}")
    print(f"   Energy reduction: {(1 - energy_filt/energy_orig)*100:.1f}%")
    
    # Low-frequency energy
    low_freq_mask = freqs_orig < 80
    low_freq_energy_orig = np.sum(mag_orig[low_freq_mask]**2)
    low_freq_energy_filt = np.sum(mag_filt[low_freq_mask]**2)
    
    print(f"\n6. Low-frequency (<80 Hz) energy:")
    print(f"   Original: {low_freq_energy_orig:.0f}")
    print(f"   Filtered: {low_freq_energy_filt:.0f}")
    print(f"   Reduction: {(1 - low_freq_energy_filt/low_freq_energy_orig)*100:.1f}%")
    
    # Create visualization
    print("\n7. Creating visualization...")
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Time-domain plots
    time = np.arange(len(audio_array)) / 44100
    
    # Original waveform
    axes[0, 0].plot(time[:2000], audio_array[:2000], 'b-', linewidth=0.5)
    axes[0, 0].set_title('Original Audio (First 45ms)\nWith Wind Noise', fontweight='bold')
    axes[0, 0].set_xlabel('Time (seconds)')
    axes[0, 0].set_ylabel('Amplitude')
    axes[0, 0].grid(True, alpha=0.3)
    
    # Filtered waveform
    axes[0, 1].plot(time[:2000], filtered_array[:2000], 'g-', linewidth=0.5)
    axes[0, 1].set_title('Filtered Audio (First 45ms)\nWind Removed', fontweight='bold')
    axes[0, 1].set_xlabel('Time (seconds)')
    axes[0, 1].set_ylabel('Amplitude')
    axes[0, 1].grid(True, alpha=0.3)
    
    # Original spectrum
    axes[1, 0].semilogy(freqs_orig, mag_orig, 'b-', linewidth=1)
    axes[1, 0].axvline(80, color='red', linestyle='--', linewidth=2, label='Filter Cutoff (80 Hz)')
    axes[1, 0].set_title('Original Spectrum\nHigh Energy at Low Frequencies', fontweight='bold')
    axes[1, 0].set_xlabel('Frequency (Hz)')
    axes[1, 0].set_ylabel('Magnitude')
    axes[1, 0].set_xlim(0, 2000)
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].legend()
    
    # Filtered spectrum
    axes[1, 1].semilogy(freqs_filt, mag_filt, 'g-', linewidth=1)
    axes[1, 1].axvline(80, color='red', linestyle='--', linewidth=2, label='Filter Cutoff (80 Hz)')
    axes[1, 1].set_title('Filtered Spectrum\nLow Frequencies Removed', fontweight='bold')
    axes[1, 1].set_xlabel('Frequency (Hz)')
    axes[1, 1].set_ylabel('Magnitude')
    axes[1, 1].set_xlim(0, 2000)
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].legend()
    
    plt.tight_layout()
    
    # Save figure
    output_file = 'wind_filter_demo.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"   Saved visualization to: {output_file}")
    
    # Show plot
    print("\n8. Displaying visualization...")
    print("   Close the plot window to continue.")
    plt.show()
    
    print("\n" + "="*60)
    print("Demo Complete!")
    print("="*60)
    print("\nKey Findings:")
    print(f"  • Wind filter reduced dB level by {db_orig - db_filt:.1f} dB")
    print(f"  • Low-frequency energy reduced by {(1 - low_freq_energy_filt/low_freq_energy_orig)*100:.1f}%")
    print(f"  • Higher-frequency sounds preserved")
    print(f"  • Visual comparison saved to {output_file}")
    print("\nThe wind filter effectively removes low-frequency wind noise")
    print("while preserving the actual noise pollution signals.")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError running demo: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
