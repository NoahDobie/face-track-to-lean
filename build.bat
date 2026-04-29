@echo off
pyinstaller --noconfirm --onefile --windowed ^
  --icon "src\icons\FTL-Icon.ico" ^
  --name "Face Track to Lean" ^
  --add-data "config;config/" ^
  --add-data "src\icons;icons/" ^
  --hidden-import "tkinter" ^
  --hidden-import "pynput.keyboard" ^
  --hidden-import "pygrabber.dshow_graph" ^
  --collect-data "ttkbootstrap" ^
  --collect-data "mediapipe" ^
  "src\main.py"
