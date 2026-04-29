import tkinter as tk
import ttkbootstrap as ttkb

def create_camera_select_frame(root, controller):
    frame = ttkb.Frame(root, borderwidth=1, relief="solid", padding=8)
    frame.pack(side=tk.TOP, pady=5)

    ttkb.Label(frame, text="Select Camera:", bootstyle="dark", foreground="white").pack(padx=5)
    camera_var = tk.StringVar()
    dropdown_list = ttkb.Combobox(frame, textvariable=camera_var, bootstyle="dark", state="readonly")
    dropdown_list.pack(padx=5, pady=5)

    # Get the camera names and indices
    camera_dict = controller.list_cameras()
    camera_names = list(camera_dict.keys())
    dropdown_list['values'] = camera_names

    if camera_names:
        dropdown_list.current(0)
        controller.selected_camera_index = camera_dict[camera_names[0]]

    # Update the selected camera index in the controller
    def update_camera_index(event):
        selected_camera = dropdown_list.get()
        controller.selected_camera_index = camera_dict[selected_camera]
        controller.switch_camera()

    dropdown_list.bind("<<ComboboxSelected>>", update_camera_index)

    return frame, camera_var, dropdown_list