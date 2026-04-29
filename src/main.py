import os
import sys
import shutil
import tkinter as tk
import logging
from controller import Controller
import cv2
from PIL import Image, ImageTk

logging.basicConfig(level=logging.DEBUG)

def get_config_path():
    """Return a writable config path.

    EXE: stored next to the EXE; default is seeded from the bundled copy on first run.
    Dev: relative to this file so it works regardless of CWD.
    """
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        config_path = os.path.join(exe_dir, 'config', 'config.properties')
        if not os.path.exists(config_path):
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            shutil.copy(
                os.path.join(sys._MEIPASS, 'config', 'config.properties'),
                config_path,
            )
        return config_path
    else:
        return os.path.normpath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config', 'config.properties')
        )

CONFIG_PATH = get_config_path()
logging.debug(f"Config path: {CONFIG_PATH}")

if __name__ == "__main__":
    app = None
    try:
        root = tk.Tk()
        app = Controller(root, config_path=CONFIG_PATH)
        root.mainloop()
    except KeyboardInterrupt:
        logging.info("Program interrupted by user.")
    except Exception as e:
        logging.error(f"Unhandled exception: {e}")
    finally:
        if app and app.face_tracker:
            app.face_tracker.release()
        cv2.destroyAllWindows()