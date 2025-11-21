<p align="center">
  <img src="imgs/banner.png" alt="PS Vita Media Processor Logo" width="700">
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.8%2B-blue.svg" alt="Python Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
  <a href="https://pypi.org/project/psvmp/"><img src="https://img.shields.io/pypi/v/psvmp.svg" alt="PyPI Version"></a>
</p>

---

> **Note:** The GUI components were removed so the application can run as a standalone tool. The GUI version is available in the releases.
> Sometimes the app may not work properly — make sure you update `yt-dlp` or any external tool you are using.

## Supported Sources

* **Mega.nz** — via `megatools`
* **YouTube** — via `yt-dlp`
* **SoundCloud** — audio-only support with metadata preservation
* **Other websites** — generic support via `yt-dlp`

## Requirements

* Python 3.8 or later  
* FFmpeg  
* yt-dlp  
* megatools
* PS Vita with VitaShell (FTP enabled)

## Installation

### Method 1: PyPI Installation (Recommended)

```bash
pip install psvmp
````

### Method 2: Manual Installation

#### 1. Clone the repository

```bash
git clone https://github.com/v7upSln/PSVMP.git
cd PSVMP
```

#### 2. Install Python dependencies

```bash
pip install tqdm yt-dlp PyQt6
```

#### 3. Install system dependencies

##### Windows

* Download FFmpeg
* Download megatools
* Install yt-dlp:

```bash
pip install yt-dlp
```

##### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install ffmpeg megatools
pip install yt-dlp PyQt6
```

##### macOS

```bash
brew install ffmpeg megatools
pip install yt-dlp PyQt6
```

#### 4. Verify installation

```bash
python psmedia.py --check-deps
```

## PS Vita Setup

1. Install VitaShell on your PS Vita
2. Launch VitaShell and press `SELECT` to start the FTP server
3. Note the **IP** and **Port** shown on the PS Vita
4. Ensure your computer and PS Vita are on the same network

## Usage

#### Basic Examples

YouTube video:

```bash
python psmedia.py "https://www.youtube.com/watch?v=VIDEO_ID" --type video
```

SoundCloud music:

```bash
python psmedia.py "https://soundcloud.com/artist/track" --type music
```

Mega.nz:

```bash
python psmedia.py "https://mega.nz/file/..." --ip 192.168.1.100 --port 1337
```

Version:

```bash
python psmedia.py --version
```

## Command Line Options

```
usage: psmedia.py [-h] [--type {video,music}] [--ip IP] [--port PORT]
                  [--check-deps] [-v] [-u] [--history] [--history-clear]
                  [--history-limit HISTORY_LIMIT] [--config]
                  [--config-set KEY=VALUE] [--config-show]
                  [url]

PS Vita Media Processor

positional arguments:
  url                   URL of the media file (Mega.nz, YouTube, SoundCloud,
                        etc.)

options:
  -h, --help            show this help message and exit
  --type {video,music}  Type of media to process (default: video)
  --ip IP               PS Vita IP address (default: 192.168.1.7)
  --port PORT           PS Vita FTP port (default: 1337)
  --check-deps          Check if required dependencies are installed
  -v, --version         Show version information and exit
  -u, --update          Check for updates and exit
  --history             Show download history
  --history-clear       Clear download history
  --history-limit HISTORY_LIMIT
                        Number of history entries to show (default: 10)

configuration options:
  --config, -c          Show configuration file location and current settings
  --config-set KEY=VALUE
                        Set configuration value (can be used multiple times)
  --config-show         Show current configuration
```

## Tutorial

<p align="center">
  <a href="https://www.youtube.com/watch?v=Ej24JAy4vIM">
    <img src="https://img.youtube.com/vi/Ej24JAy4vIM/hqdefault.jpg" width="720" alt="Watch the tutorial video">
  </a>
</p>

## File Organization

```
Documents/PSvita media processer/
├── temp/           # Temporary downloads
└── converted/      # Files ready for PS Vita
```

## Output Locations

* Videos → `ux0:/video/shows/`
* Music → `ux0:/music/`

## Technical Details

### Video Conversion

* Resolution: 960×544
* Codec: H.264 Baseline
* Bitrate: 1500k (max 2000k)
* Audio: AAC 128kbps

### Audio Conversion

* MP3 at 320kbps
* 44.1kHz
* Metadata preserved

## Troubleshooting

### “Missing required tools”

* Run: `python psmedia.py --check-deps`
* Install missing dependencies

### FTP connection issues

* Ensure VitaShell FTP is active
* Confirm IP/port
* Same network required

### Download failed

* Retry
* Update `yt-dlp`
* Check Mega link validity

### Conversion failed

* Ensure file integrity
* Verify FFmpeg installation
* Try another source

## License

This project is licensed under the [MIT License](LICENSE)

## Acknowledgments

* VitaShell team
* FFmpeg team
* yt-dlp developers
* megatools developers

---

<p align="center"><b>Made with ❤️ for the PS Vita community</b></p>
