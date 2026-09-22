import json
import os
import sys
import tkinter as tk
from tkinter import colorchooser, font, messagebox
from PIL import Image, ImageTk  # Requires: pip install Pillow

SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
SETTINGS_FILE = os.path.join(SCRIPT_DIR, "overlay_settings.json")
FONTS_DIR = os.path.join(SCRIPT_DIR, "fonts")
BG_IMAGE_PATH = os.path.join(SCRIPT_DIR, "window_bg.png")
LOGO_IMAGE_PATH = os.path.join(SCRIPT_DIR, "logo.png")

DEFAULT_FONT_FILE = "DefaultFont.ttf"
DEFAULT_TEXT_COLOR = (225, 225, 225, 255)
DEFAULT_DEAD_TEXT_COLOR = (255, 0, 0, 255)
DEFAULT_FONT_SIZE = 18
DEFAULT_TEXT_OUTLINE_WIDTH = 1
DEFAULT_TEXT_OUTLINE_COLOR = (0, 0, 0, 255)
DEFAULT_USE_TEXT_BACKGROUND = True
DEFAULT_SHOW_MOUSEOVER_ONLY = False

DEFAULT_BASE_HEIGHT = 10
DEFAULT_LEFT_CAP_WIDTH = 5
DEFAULT_RIGHT_CAP_WIDTH = 5
DEFAULT_FILL_HEIGHT = 6
DEFAULT_BOSS_ICON_BASE_SIZE = 30
DEFAULT_CLOSE_RANGE_THRESHOLD = 400
DEFAULT_SHORTEN_NUMBER_DIGITS = 3

RESOLUTION_OPTIONS = [
    "640x480",
    "800x600",
    "1024x768",
    "1152x864",
    "1280x720",
    "1280x800",
    "1280x960",
    "1280x1024",
    "1366x768",
    "1400x1050",
    "1440x900",
    "1600x900",
    "1600x1200",
    "1680x1050",
    "1920x1080",
    "1920x1200",
    "2048x1536",
    "2560x1080",
    "2560x1440",
    "2560x1600",
    "2880x1800",
    "3000x2000",
    "3200x1800",
    "3440x1440",
    "3840x1080",
    "3840x1600",
    "3840x2160",
    "3840x2400",
    "5120x1440",
    "5120x2160",
    "5120x2880",
    "7680x2160",
    "7680x4320",
]
DEFAULT_RESOLUTION = "1920x1080"


class SettingsApp:

    def __init__(self, master):
        self.master = master
        master.title("Overlay Settings")

        self.window_width = 720
        self.window_height = 540
        master.geometry(f"{self.window_width}x{self.window_height}")
        master.resizable(False, False)

        self.settings = self.load_settings()

        self.canvas = tk.Canvas(
            master,
            width=self.window_width,
            height=self.window_height,
            highlightthickness=0,
            bg="#101514",
        )
        self.canvas.pack(fill="both", expand=True)

        self.load_background_image()

        self.bg_sample_color = "#2b3533"
        self.fg_color = "#e2e8e6"
        self.widget_bg = "#3a4644"

        self.create_layout()
        self.apply_settings_to_widgets()

    def load_background_image(self):
        """Loads window_bg.png directly on canvas background."""
        if os.path.exists(BG_IMAGE_PATH):
            try:
                bg_img = Image.open(BG_IMAGE_PATH).resize(
                    (self.window_width, self.window_height),
                    Image.Resampling.LANCZOS,
                )
                self.bg_photo = ImageTk.PhotoImage(bg_img)
                self.canvas.create_image(0, 0, image=self.bg_photo, anchor="nw")
            except Exception as e:
                print(f"Error loading background image: {e}")

    def load_logo_image(self, parent_frame):
        """Loads and embeds logo.png centered in the lower-left area of the menu."""
        if os.path.exists(LOGO_IMAGE_PATH):
            try:
                logo_img = Image.open(LOGO_IMAGE_PATH)
                logo_img.thumbnail((300, 80), Image.Resampling.LANCZOS)
                
                self.logo_photo = ImageTk.PhotoImage(logo_img)
                logo_label = tk.Label(
                    parent_frame,
                    image=self.logo_photo,
                    bg=self.bg_sample_color,
                )
                logo_label.pack(side="bottom", anchor="center", expand=True, pady=10)
            except Exception as e:
                print(f"Error loading logo image: {e}")

    def load_settings(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    settings = json.load(f)
                    default_settings = self.get_default_settings()
                    for key, default_value in default_settings.items():
                        if key not in settings:
                            settings[key] = default_value
                    return settings
            else:
                return self.get_default_settings()
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading settings: {e}. Using default settings.")
            return self.get_default_settings()

    def get_default_settings(self):
        return {
            "font_file": DEFAULT_FONT_FILE,
            "font_size": DEFAULT_FONT_SIZE,
            "text_color": list(DEFAULT_TEXT_COLOR),
            "text_outline_width": DEFAULT_TEXT_OUTLINE_WIDTH,
            "text_outline_color": list(DEFAULT_TEXT_OUTLINE_COLOR),
            "use_text_background": DEFAULT_USE_TEXT_BACKGROUND,
            "show_mouseover_only": DEFAULT_SHOW_MOUSEOVER_ONLY,
            "base_height": DEFAULT_BASE_HEIGHT,
            "left_cap_width": DEFAULT_LEFT_CAP_WIDTH,
            "right_cap_width": DEFAULT_RIGHT_CAP_WIDTH,
            "fill_height": DEFAULT_FILL_HEIGHT,
            "boss_icon_base_size": DEFAULT_BOSS_ICON_BASE_SIZE,
            "close_range_threshold": DEFAULT_CLOSE_RANGE_THRESHOLD,
            "shorten_number_digits": DEFAULT_SHORTEN_NUMBER_DIGITS,
            "screen_resolution": DEFAULT_RESOLUTION,
        }

    def save_settings(self):
        current_settings = {
            "font_file": self.font_file_var.get(),
            "font_size": self.font_size_var.get(),
            "text_color": self.text_color_rgb,
            "text_outline_width": self.text_outline_width_var.get(),
            "text_outline_color": self.text_outline_color_rgb,
            "use_text_background": self.use_text_background_var.get(),
            "show_mouseover_only": self.show_mouseover_only_var.get(),
            "base_height": self.base_height_var.get(),
            "left_cap_width": self.left_cap_width_var.get(),
            "right_cap_width": self.right_cap_width_var.get(),
            "fill_height": self.fill_height_var.get(),
            "boss_icon_base_size": self.boss_icon_base_size_var.get(),
            "close_range_threshold": self.close_range_threshold_var.get(),
            "shorten_number_digits": self.shorten_number_digits_var.get(),
            "screen_resolution": self.resolution_var.get(),
        }
        try:
            os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
            with open(SETTINGS_FILE, "w") as f:
                json.dump(current_settings, f, indent=4)
        except IOError as e:
            print(f"Error saving settings: {e}")

    def update_live_overlay(self, *args):
        self.save_settings()

    def choose_font(self):
        font_files = [
            f
            for f in os.listdir(FONTS_DIR)
            if f.lower().endswith((".ttf", ".otf"))
        ]
        if not font_files:
            messagebox.showwarning(
                "No Fonts Found",
                f"No .ttf or .otf font files found in '{FONTS_DIR}'.",
            )
            return

        top = tk.Toplevel(self.master)
        top.title("Select Font")

        self.master.update_idletasks()
        top_w, top_h = 220, 280

        parent_x = self.master.winfo_rootx()
        parent_y = self.master.winfo_rooty()
        parent_w = self.master.winfo_width()
        parent_h = self.master.winfo_height()

        pos_x = parent_x + (parent_w // 2) - (top_w // 2)
        pos_y = parent_y + (parent_h // 2) - (top_h // 2)

        top.geometry(f"{top_w}x{top_h}+{pos_x}+{pos_y}")
        top.transient(self.master)
        top.grab_set()

        listbox_frame = tk.Frame(top)
        listbox_frame.pack(padx=10, pady=10, fill="both", expand=True)

        scrollbar = tk.Scrollbar(listbox_frame, orient="vertical")
        listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set)
        scrollbar.config(command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True)

        for f_name in font_files:
            listbox.insert(tk.END, f_name)

        try:
            current_font_index = font_files.index(self.font_file_var.get())
            listbox.selection_set(current_font_index)
            listbox.see(current_font_index)
        except ValueError:
            pass

        def on_select():
            selected_index = listbox.curselection()
            if selected_index:
                selected_font = listbox.get(selected_index[0])
                self.font_file_var.set(selected_font)
                self.update_live_overlay()
            top.destroy()

        select_button = tk.Button(top, text="Select", command=on_select)
        select_button.pack(pady=5)

    def choose_color(self, color_var, color_display_label, is_outline=False):
        initial_color = (
            self.rgb_to_hex(color_var)
            if isinstance(color_var, list)
            else "#FFFFFF"
        )
        color_code = colorchooser.askcolor(initialcolor=initial_color)
        if color_code[1]:
            rgb = color_code[0]
            new_color_rgba = [int(c) for c in rgb] + [255]

            if is_outline:
                self.text_outline_color_rgb = new_color_rgba
            else:
                self.text_color_rgb = new_color_rgba

            color_display_label.config(bg=color_code[1])
            self.update_live_overlay()

    def rgb_to_hex(self, rgb_list):
        if len(rgb_list) == 4:
            rgb_list = rgb_list[:3]
        return f"#{rgb_list[0]:02x}{rgb_list[1]:02x}{rgb_list[2]:02x}"

    def apply_settings_to_widgets(self):
        self.font_file_var.set(self.settings["font_file"])
        self.font_size_var.set(self.settings["font_size"])
        self.text_color_rgb = list(self.settings["text_color"])
        self.text_outline_width_var.set(self.settings["text_outline_width"])
        self.text_outline_color_rgb = list(
            self.settings["text_outline_color"]
        )
        self.use_text_background_var.set(self.settings["use_text_background"])
        self.show_mouseover_only_var.set(self.settings.get("show_mouseover_only", DEFAULT_SHOW_MOUSEOVER_ONLY))

        self.base_height_var.set(self.settings["base_height"])
        self.left_cap_width_var.set(self.settings["left_cap_width"])
        self.right_cap_width_var.set(self.settings["right_cap_width"])
        self.fill_height_var.set(self.settings["fill_height"])
        self.boss_icon_base_size_var.set(self.settings["boss_icon_base_size"])
        self.close_range_threshold_var.set(
            self.settings["close_range_threshold"]
        )
        self.shorten_number_digits_var.set(
            self.settings["shorten_number_digits"]
        )

        self.resolution_var.set(
            self.settings.get("screen_resolution", DEFAULT_RESOLUTION)
        )

        self.text_color_display.config(bg=self.rgb_to_hex(self.text_color_rgb))
        self.text_outline_color_display.config(
            bg=self.rgb_to_hex(self.text_outline_color_rgb)
        )

    def restore_defaults(self):
        confirm = messagebox.askyesno(
            "Restore Defaults",
            "Are you sure you want to restore all settings to their default values?",
        )
        if confirm:
            self.settings = self.get_default_settings()
            self.apply_settings_to_widgets()
            self.save_settings()
            messagebox.showinfo(
                "Defaults Restored",
                "All settings have been restored to defaults.",
            )

    def make_section_frame(self, parent, title):
        return tk.LabelFrame(
            parent,
            text=title,
            bg=self.bg_sample_color,
            fg=self.fg_color,
            bd=1,
            relief="groove",
            font=("Segoe UI", 9, "bold"),
        )

    def create_layout(self):
        # 1. Top Header Section
        header_frame = tk.Frame(self.master, bg=self.bg_sample_color)
        self.canvas.create_window(
            25, 20, anchor="nw", window=header_frame, width=670, height=35
        )

        self.resolution_var = tk.StringVar()
        tk.Label(
            header_frame,
            text="Screen Resolution:",
            bg=self.bg_sample_color,
            fg=self.fg_color,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=10)

        res_dropdown = tk.OptionMenu(
            header_frame,
            self.resolution_var,
            *RESOLUTION_OPTIONS,
            command=self.update_live_overlay,
        )
        res_dropdown.config(
            bg=self.widget_bg, fg=self.fg_color, activebackground="#4e5c5a"
        )
        res_dropdown["menu"].config(bg=self.widget_bg, fg=self.fg_color)
        res_dropdown.pack(side="left", padx=5)

        restore_button = tk.Button(
            header_frame,
            text="Restore Defaults",
            command=self.restore_defaults,
            bg=self.widget_bg,
            fg=self.fg_color,
            activebackground="#4e5c5a",
            activeforeground=self.fg_color,
        )
        restore_button.pack(side="right", padx=10)

        # 2. Left Column
        left_panel = tk.Frame(self.master, bg=self.bg_sample_color)
        self.canvas.create_window(
            25, 70, anchor="nw", window=left_panel, width=325, height=440
        )

        # 3. Right Column
        right_panel = tk.Frame(self.master, bg=self.bg_sample_color)
        self.canvas.create_window(
            370, 70, anchor="nw", window=right_panel, width=325, height=440
        )

        # --- Left Column Settings ---
        font_frame = self.make_section_frame(left_panel, "Font Settings")
        font_frame.pack(fill="x", padx=5, pady=6)

        self.font_file_var = tk.StringVar()
        tk.Label(
            font_frame,
            text="Font File:",
            bg=self.bg_sample_color,
            fg=self.fg_color,
        ).grid(row=0, column=0, sticky="w", padx=4)

        tk.Entry(
            font_frame,
            textvariable=self.font_file_var,
            state="readonly",
            width=18,
            bg="#1b2221",
            fg="#ffffff",
            readonlybackground="#1b2221",
            disabledforeground="#ffffff",
        ).grid(row=0, column=1, sticky="ew", padx=2, pady=2)

        tk.Button(
            font_frame,
            text="Browse",
            command=self.choose_font,
            bg=self.widget_bg,
            fg=self.fg_color,
        ).grid(row=0, column=2, sticky="e", padx=2)

        self.font_size_var = tk.IntVar()
        tk.Label(
            font_frame,
            text="Font Size:",
            bg=self.bg_sample_color,
            fg=self.fg_color,
        ).grid(row=1, column=0, sticky="w", padx=4)
        tk.Scale(
            font_frame,
            from_=8,
            to=48,
            orient="h",
            variable=self.font_size_var,
            command=self.update_live_overlay,
            bg=self.bg_sample_color,
            fg=self.fg_color,
            highlightthickness=0,
        ).grid(row=1, column=1, columnspan=2, sticky="ew")

        color_frame = self.make_section_frame(left_panel, "Text Color Settings")
        color_frame.pack(fill="x", padx=5, pady=6)

        self.text_color_rgb = []
        tk.Label(
            color_frame,
            text="Text Color:",
            bg=self.bg_sample_color,
            fg=self.fg_color,
        ).grid(row=0, column=0, sticky="w", padx=4)
        self.text_color_display = tk.Label(
            color_frame, width=4, relief="sunken"
        )
        self.text_color_display.grid(
            row=0, column=1, padx=4, pady=2, sticky="ew"
        )
        tk.Button(
            color_frame,
            text="Choose",
            command=lambda: self.choose_color(
                self.text_color_rgb, self.text_color_display, False
            ),
            bg=self.widget_bg,
            fg=self.fg_color,
        ).grid(row=0, column=2, sticky="e", padx=2)

        self.text_outline_width_var = tk.IntVar()
        tk.Label(
            color_frame,
            text="Outline Width:",
            bg=self.bg_sample_color,
            fg=self.fg_color,
        ).grid(row=1, column=0, sticky="w", padx=4)
        tk.Scale(
            color_frame,
            from_=0,
            to=5,
            orient="h",
            variable=self.text_outline_width_var,
            command=self.update_live_overlay,
            bg=self.bg_sample_color,
            fg=self.fg_color,
            highlightthickness=0,
        ).grid(row=1, column=1, columnspan=2, sticky="ew")

        self.text_outline_color_rgb = []
        tk.Label(
            color_frame,
            text="Outline Color:",
            bg=self.bg_sample_color,
            fg=self.fg_color,
        ).grid(row=2, column=0, sticky="w", padx=4)
        self.text_outline_color_display = tk.Label(
            color_frame, width=4, relief="sunken"
        )
        self.text_outline_color_display.grid(
            row=2, column=1, padx=4, pady=2, sticky="ew"
        )
        tk.Button(
            color_frame,
            text="Choose",
            command=lambda: self.choose_color(
                self.text_outline_color_rgb,
                self.text_outline_color_display,
                True,
            ),
            bg=self.widget_bg,
            fg=self.fg_color,
        ).grid(row=2, column=2, sticky="e", padx=2)

        self.use_text_background_var = tk.BooleanVar()
        tk.Checkbutton(
            color_frame,
            text="Use Text Background",
            variable=self.use_text_background_var,
            command=self.update_live_overlay,
            bg=self.bg_sample_color,
            fg=self.fg_color,
            selectcolor="#1b2221",
            activebackground=self.bg_sample_color,
            activeforeground=self.fg_color,
        ).grid(row=3, column=0, columnspan=3, sticky="w", padx=4, pady=2)

        # --- Display Options Section ---
        display_frame = self.make_section_frame(left_panel, "Display Options")
        display_frame.pack(fill="x", padx=5, pady=6)

        self.show_mouseover_only_var = tk.BooleanVar()
        tk.Checkbutton(
            display_frame,
            text="Show Mouseover Target Only",
            variable=self.show_mouseover_only_var,
            command=self.update_live_overlay,
            bg=self.bg_sample_color,
            fg=self.fg_color,
            selectcolor="#1b2221",
            activebackground=self.bg_sample_color,
            activeforeground=self.fg_color,
        ).pack(anchor="w", padx=4, pady=4)

        # Centered Lower-Left Logo Image
        self.load_logo_image(left_panel)

        # --- Right Column Settings ---
        bar_frame = self.make_section_frame(right_panel, "Bar Dimensions")
        bar_frame.pack(fill="x", padx=5, pady=6)

        self.base_height_var = tk.IntVar()
        tk.Label(
            bar_frame,
            text="Base Height:",
            bg=self.bg_sample_color,
            fg=self.fg_color,
        ).grid(row=0, column=0, sticky="w", padx=4)
        tk.Scale(
            bar_frame,
            from_=5,
            to=50,
            orient="h",
            variable=self.base_height_var,
            command=self.update_live_overlay,
            bg=self.bg_sample_color,
            fg=self.fg_color,
            highlightthickness=0,
        ).grid(row=0, column=1, sticky="ew")

        self.left_cap_width_var = tk.IntVar()
        tk.Label(
            bar_frame,
            text="Left Cap Width:",
            bg=self.bg_sample_color,
            fg=self.fg_color,
        ).grid(row=1, column=0, sticky="w", padx=4)
        tk.Scale(
            bar_frame,
            from_=0,
            to=20,
            orient="h",
            variable=self.left_cap_width_var,
            command=self.update_live_overlay,
            bg=self.bg_sample_color,
            fg=self.fg_color,
            highlightthickness=0,
        ).grid(row=1, column=1, sticky="ew")

        self.right_cap_width_var = tk.IntVar()
        tk.Label(
            bar_frame,
            text="Right Cap Width:",
            bg=self.bg_sample_color,
            fg=self.fg_color,
        ).grid(row=2, column=0, sticky="w", padx=4)
        tk.Scale(
            bar_frame,
            from_=0,
            to=20,
            orient="h",
            variable=self.right_cap_width_var,
            command=self.update_live_overlay,
            bg=self.bg_sample_color,
            fg=self.fg_color,
            highlightthickness=0,
        ).grid(row=2, column=1, sticky="ew")

        self.fill_height_var = tk.IntVar()
        tk.Label(
            bar_frame,
            text="Fill Height:",
            bg=self.bg_sample_color,
            fg=self.fg_color,
        ).grid(row=3, column=0, sticky="w", padx=4)
        tk.Scale(
            bar_frame,
            from_=1,
            to=40,
            orient="h",
            variable=self.fill_height_var,
            command=self.update_live_overlay,
            bg=self.bg_sample_color,
            fg=self.fg_color,
            highlightthickness=0,
        ).grid(row=3, column=1, sticky="ew")

        self.boss_icon_base_size_var = tk.IntVar()
        tk.Label(
            bar_frame,
            text="Boss Icon Size:",
            bg=self.bg_sample_color,
            fg=self.fg_color,
        ).grid(row=4, column=0, sticky="w", padx=4)
        tk.Scale(
            bar_frame,
            from_=10,
            to=100,
            orient="h",
            variable=self.boss_icon_base_size_var,
            command=self.update_live_overlay,
            bg=self.bg_sample_color,
            fg=self.fg_color,
            highlightthickness=0,
        ).grid(row=4, column=1, sticky="ew")

        close_frame = self.make_section_frame(
            right_panel, "Close Range Stacking"
        )
        close_frame.pack(fill="x", padx=5, pady=6)

        self.close_range_threshold_var = tk.IntVar()
        tk.Label(
            close_frame,
            text="Threshold (0=Off):",
            bg=self.bg_sample_color,
            fg=self.fg_color,
        ).grid(row=0, column=0, sticky="w", padx=4)
        tk.Scale(
            close_frame,
            from_=0,
            to=1000,
            orient="h",
            variable=self.close_range_threshold_var,
            command=self.update_live_overlay,
            bg=self.bg_sample_color,
            fg=self.fg_color,
            highlightthickness=0,
        ).grid(row=0, column=1, sticky="ew")

        short_frame = self.make_section_frame(right_panel, "Number Shortening")
        short_frame.pack(fill="x", padx=5, pady=6)

        self.shorten_number_digits_var = tk.IntVar()
        tk.Label(
            short_frame,
            text="Shortening Digits:",
            bg=self.bg_sample_color,
            fg=self.fg_color,
        ).grid(row=0, column=0, sticky="w", padx=4)
        tk.Scale(
            short_frame,
            from_=1,
            to=10,
            orient="h",
            variable=self.shorten_number_digits_var,
            command=self.update_live_overlay,
            bg=self.bg_sample_color,
            fg=self.fg_color,
            highlightthickness=0,
        ).grid(row=0, column=1, sticky="ew")

        font_frame.grid_columnconfigure(1, weight=1)
        color_frame.grid_columnconfigure(1, weight=1)
        bar_frame.grid_columnconfigure(1, weight=1)
        close_frame.grid_columnconfigure(1, weight=1)
        short_frame.grid_columnconfigure(1, weight=1)

        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        self.save_settings()
        self.master.destroy()


def main():
    root = tk.Tk()
    app = SettingsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()