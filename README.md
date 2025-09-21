# EEG-OSC Bridge

Real-time EEG data processing and OSC forwarding for creative applications.

## What it does

Grabs EEG data from LSL streams, processes it (filtering, artifact removal, band power analysis), and sends everything over OSC. Useful for interactive installations, live performances, or any project where you need clean EEG data flowing into other software.

## Requirements

```bash
pip install pylsl python-osc numpy scipy
```

## Usage

Just run it:
```bash
python LSL->OSC.py
```

The script automatically finds EEG streams and starts pumping data to `127.0.0.1:5008`. 

## Configuration

Edit the parameters at the top of the file:

- `osc_ip`, `osc_port` - where to send OSC messages
- `send_processed` - 0 for raw data, 1 for filtered + band powers
- `lowcut`, `highcut` - bandpass filter range
- `max_channels` - limit number of channels processed

## OSC Output

**Raw mode:** sends individual channel values as `/ChannelName`

**Processed mode:** sends:
- Band powers: `/Delta`, `/Theta`, `/Alpha`, `/Beta`, `/Gamma`  
- Filtered channel data: `/ChannelName`

## Notes

- Expects 500Hz sampling rate for optimal performance
- Built for 8-channel setups but configurable
- Press Ctrl+C to stop

Works with any LSL-compatible EEG device. Tested with BrainTech Perun-8, Muse, Unicorn and similar hardware.
