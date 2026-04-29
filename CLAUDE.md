# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```sh
# Run the app
python src/main.py

# Install dependencies
pip install -r requirements.txt

# Build a standalone EXE
pyinstaller --noconfirm --onefile --windowed \
  --icon "src/icons/FTL-Icon.ico" \
  --name "Face Track to Lean" \
  --add-data "config;config/" \
  --add-data "config/config.properties;." \
  --hidden-import "tkinter" \
  --hidden-import "ttkbootstrap" \
  --hidden-import "cv2" \
  --hidden-import "PIL.Image" \
  --hidden-import "PIL.ImageTK" \
  --hidden-import "pynput.keyboard" \
  --hidden-import "pygrabber.dshow_graph" \
  "src/main.py"
```

There are no automated tests.

## Architecture

The app follows an MVC pattern with three main layers:

**`src/main.py`** — Entry point. Resolves the config path for both dev and PyInstaller (`sys._MEIPASS`), creates the `tk.Tk` root, instantiates `Controller`, and starts the Tkinter event loop.

**`src/controller.py` (`Controller`)** — Owns all runtime state and coordinates the other layers. Key design decisions:
- Camera initialisation runs in a background `threading.Thread` so the UI remains responsive on startup.
- A second daemon thread (`capture_and_process_frames`) continuously grabs frames and runs MediaPipe face detection, storing results behind `_frame_lock`.
- `main_loop()` is scheduled via `root.after(_MAIN_LOOP_MS)` (~30 fps) and reads from that lock — it is the only place that touches Tkinter widgets or sends keyboard events via `pynput`.
- Direction state (`"Left"` / `"Center"` / `"Right"`) is compared on each tick and keys are pressed/released only on transitions, preventing key-repeat spam.

**`src/face_tracker.py` (`FaceTracker`)** — Wraps OpenCV `VideoCapture` and a MediaPipe `FaceMesh`. `capture_frame()` reads a raw BGR frame; `process_frame()` resizes, converts to RGB, and returns landmark results.

**`src/gui.py` (`GUI`)** — Builds the Tkinter/ttkbootstrap window by calling factory functions in `src/components/`. Reads initial slider and keybind values from `controller.config` in `load_config()`.

**`src/configmanager.py` (`ConfigManager`)** — Thin `configparser` wrapper for `config/config.properties`. `update_config()` writes changes to disk immediately on every call.

**`src/components/`** — Each file exports a single `create_*` factory that builds one UI section and wires callbacks back to the controller.

## Threading model

The Tkinter event loop runs on the main thread. Two background threads exist per camera session:
1. `init_thread` — one-shot; opens the camera and starts the capture thread.
2. `capture_thread` (daemon) — runs `capture_and_process_frames()` in a tight loop, writing to `_latest_frame` / `_latest_results` under `_frame_lock`.

`main_loop()` reads those fields under the lock and does all rendering and input injection. Never write to Tkinter widgets from a background thread.

## Configuration

`config/config.properties` (INI `[DEFAULT]` section) must be bundled alongside the EXE. `main.py` resolves its path via `resource_path()` which checks `sys._MEIPASS` first. All values are read at startup; mutations are written back immediately by `ConfigManager.update_config()`.
