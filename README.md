# Face Track to Lean

Face Track to Lean is a Python application that uses your webcam to detect left and right head leaning movements and translates them into keyboard inputs. Originally built to get more immersed in Rainbow Six Siege. **by Noah Dobie**

![FTL Screenshot](https://github.com/user-attachments/assets/1bcafb09-e269-4944-aa2c-9f038e629ef2)

## Features

- Real-time face tracking using MediaPipe
- Customisable left/right boundary lines
- Customisable keyboard bindings
- Camera flip and preview toggle
- Settings persist between sessions

## Download

Grab the latest `.exe` from the [Releases](../../releases) page. No installation required — just run it.

> First launch: Windows may show a SmartScreen warning. Click **More info → Run anyway**.

## Running from Source

**Prerequisites:** Python 3.11+

```sh
git clone https://github.com/NoahDobie/Face-Track-To-Lean
cd Face-Track-To-Lean
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python src/main.py
```

## Building the EXE

With the venv active, run from the repo root:

```sh
.\build.bat
```

Output: `dist\Face Track to Lean.exe`

## Configuration

Settings are saved automatically when changed in the app. The config file lives next to the EXE at `config\config.properties`.

| Setting | Default |
|---|---|
| Left lean key | `q` |
| Right lean key | `e` |
| Start/stop toggle key | `]` |
| Left line position | 150 |
| Right line position | 210 |
