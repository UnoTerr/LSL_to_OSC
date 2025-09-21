from pylsl import StreamInlet, resolve_byprop
from pythonosc import udp_client
import numpy as np
from scipy.signal import butter, filtfilt, iirnotch, welch
import time

# Parameters
osc_ip, osc_port, max_channels, chunk_size = "127.0.0.1", 5008, 8, 10
processed_update_rate, lowcut, highcut, notch_freq = 8, 1.0, 50.0, 50.0
min_threshold, max_threshold, send_processed = -100, 100, 1
filter_buffer_size, bandpower_ceiling = 250, 200
band_definitions = {"Delta": (0.5, 4), "Theta": (4, 8), "Alpha": (8, 14), "Beta": (14, 30), "Gamma": (30, 50)}

def get_channel_names(info, max_channels):
    ch, names = info.desc().child("channels").child("channel"), []
    while ch and len(names) < max_channels:
        names.append(ch.child_value("label") or f"Channel_{len(names) + 1}")
        ch = ch.next_sibling()
    return names

def apply_filters(data, fs, lowcut, highcut, notch_freq):
    nyq = 0.5 * fs
    b_bp, a_bp = butter(4, [lowcut/nyq, highcut/nyq], btype='band')
    filtered = filtfilt(b_bp, a_bp, data, axis=0)
    if notch_freq:
        b_n, a_n = iirnotch(notch_freq/nyq, 30)
        filtered = filtfilt(b_n, a_n, filtered, axis=0)
    return np.clip(filtered, min_threshold, max_threshold)

def compute_band_powers(data, fs):
    freqs, psd = welch(data, fs, nperseg=fs//2, noverlap=fs//4)
    return {band: min(np.mean(psd[:, (freqs >= low) & (freqs <= high)]), bandpower_ceiling) 
            for band, (low, high) in band_definitions.items()}

def main():
    print("Looking for an EEG stream...")
    streams = resolve_byprop('type', 'EEG', timeout=5)
    if not streams: return print("No EEG stream found.")
    
    inlet = StreamInlet(streams[0])
    info = inlet.info()
    sample_rate, channel_names = info.nominal_srate(), get_channel_names(info, max_channels)
    n_channels = len(channel_names)
    print(f"Stream: {info.name()}, Type: {info.type()}, Channels: {n_channels}, Rate: {sample_rate} Hz")
    print(f"Channel names: {channel_names}")
    
    osc_client = udp_client.SimpleUDPClient(osc_ip, osc_port)
    print(f"OSC client at {osc_ip}:{osc_port}\nPress Ctrl+C to stop...")
    
    filter_buffer, buffer_index = np.zeros((filter_buffer_size, n_channels)), 0
    processed_interval, last_processed_time = 1.0 / processed_update_rate, time.time()
    
    try:
        while True:
            samples, _ = inlet.pull_chunk(timeout=0.1, max_samples=chunk_size)
            if not samples: continue
            
            samples = np.array(samples)[:, :max_channels]
            num_samples = samples.shape[0]
            filter_buffer = np.roll(filter_buffer, -num_samples, axis=0)
            filter_buffer[-num_samples:, :n_channels] = samples
            
            if send_processed == 0:
                for sample in samples:
                    for i, value in enumerate(sample[:n_channels]):
                        osc_client.send_message(f"/{channel_names[i]}", value)
            elif send_processed == 1 and time.time() - last_processed_time >= processed_interval:
                filtered_buffer = apply_filters(filter_buffer, sample_rate, lowcut, highcut, notch_freq)
                band_powers = compute_band_powers(filtered_buffer.T, sample_rate)
                
                for band, power in band_powers.items():
                    osc_client.send_message(f"/{band}", float(power))
                
                for sample in filtered_buffer[-num_samples:]:
                    for i, value in enumerate(sample[:n_channels]):
                        osc_client.send_message(f"/{channel_names[i]}", value)
                
                last_processed_time = time.time()
    
    except KeyboardInterrupt:
        print("Stopping data acquisition...")

if __name__ == "__main__":
    main()
