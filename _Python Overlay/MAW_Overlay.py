import json
import tkinter as tk
from PIL import Image, ImageTk, ImageFont, ImageDraw
import re
import os
import sys
import time
import math
import traceback
import subprocess

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
MONSTER_FILE = os.path.join(SCRIPT_DIR, "visible_monsters.json")

# Target process names to monitor for game presence
TARGET_GAME_PROCESSES = {"mm8.exe", "mm7.exe", "mm6.exe", "mm8_language.exe"}
PROCESS_CHECK_INTERVAL = 2.0  # Check process list every 2 seconds

def clear_monster_data():
    """Wipes ghost monster data on startup while preserving the valid JSON layout."""
    empty_data = {
        "Monsters": [],
        "TargetedMonsterIndex": -1  # Set to -1 or None to indicate no active target
    }
    try:
        with open(MONSTER_FILE, "w") as f:
            json.dump(empty_data, f, indent=4)
        print("Successfully cleared ghost monsters on startup.")
    except Exception as e:
        print(f"Error clearing monster data: {e}")

UPDATE_INTERVAL = 10 
SETTINGS_FILE = os.path.join(SCRIPT_DIR, "overlay_settings.json")
FONTS_DIR = os.path.join(SCRIPT_DIR, "fonts")
BOSS_ICONS_DIR = os.path.join(SCRIPT_DIR, "boss icons")
ERROR_LOG_FILE = os.path.join(SCRIPT_DIR, "overlay_error.log")

UI_DIR = os.path.join(SCRIPT_DIR, "UI")

BACKGROUND_PATH = os.path.join(UI_DIR, "background.png")
LEFT_CAP_PATH = os.path.join(UI_DIR, "left_cap.png")
RIGHT_CAP_PATH = os.path.join(UI_DIR, "right_cap.png")

FILL_PATHS = {
    "boss": os.path.join(UI_DIR, "fill_boss.png"),
    "50": os.path.join(UI_DIR, "fill_50.png"),
    "75": os.path.join(UI_DIR, "fill_75.png"),
    "default": os.path.join(UI_DIR, "fill.png"),
    "hit": os.path.join(UI_DIR, "fill_hit.png"),
    "crit": os.path.join(UI_DIR, "fill_crit.png"),
    "text_bg": os.path.join(UI_DIR, "text_bg.png")
}

_temp_root = tk.Tk()
_temp_root.withdraw()
detected_user_res_X = _temp_root.winfo_screenwidth()
detected_user_res_Y = _temp_root.winfo_screenheight()
_temp_root.destroy()

BASE_HEIGHT = 10
LEFT_CAP_WIDTH = 5
RIGHT_CAP_WIDTH = 5
FILL_HEIGHT = 6

DEFAULT_FONT_FILE = "DefaultFont.ttf"
DEFAULT_TEXT_COLOR = (225, 225, 225, 255)
DEFAULT_DEAD_TEXT_COLOR = (255, 0, 0, 255)
DEFAULT_FONT_SIZE = 18
DEFAULT_TEXT_OUTLINE_WIDTH = 1
DEFAULT_TEXT_OUTLINE_COLOR = (0, 0, 0, 255)
DEFAULT_USE_TEXT_BACKGROUND = True

ENABLE_SCALING = True
SCALE_NEAR = 1.2
SCALE_FAR = 0.6
SCALE_NEAR_DIST = 1000
SCALE_FAR_DIST = 5000

# Grid specific configuration
GRID_BASE_SCALE = 0.75  # Starting size for grid elements
CLOSE_RANGE_THRESHOLD = 400
CLOSE_STACK_START_X = (detected_user_res_X / 2)
CLOSE_STACK_START_Y = detected_user_res_Y - 350
CLOSE_STACK_MAX_PER_COL = 3  # Force max 3 per column
CLOSE_STACK_SPACING_Y = 65
CLOSE_STACK_SPACING_X = 180

BOSS_PREFIXES = (
    "Venomous", "Leech", "Exploding", "Adamantite", "Puller",
    "Summoner", "Swift", "Regenerating", "Reflecting", "Thorn",
    "Swapper", "Fixator", "Plagueborn", "Broodlord", "Omnipotent"
)

FADE_OUT_DURATION = 0.8
RESTART_DELAY = 5

class OverlayApp:
    def __init__(self, root):
        self.root = root
        clear_monster_data()
        root.title("Monster HP Overlay")
        transparent_color = "#245132"
        root.overrideredirect(True)
        root.config(bg=transparent_color)
        root.attributes("-transparentcolor", transparent_color)
        root.attributes("-topmost", True)
        root.geometry(f"{detected_user_res_X}x{detected_user_res_Y}+0+0")

        self.canvas = tk.Canvas(root, width=detected_user_res_X, height=detected_user_res_Y,
                                bg=transparent_color, highlightthickness=0)
        self.canvas.pack()

        self.load_assets()
        self.load_settings()

        self.tk_image_references = []
        self.fading_monsters = {}
        self.permanently_hidden_monsters = set()

        self.error_occurred = False
        self.error_message = ""
        self.error_start_time = None
        
        self.last_process_check_time = 0

        self.update_loop()

    def is_game_running(self):
        """Checks if any target game process is running in Windows."""
        try:
            # 0x08000000 = CREATE_NO_WINDOW flag to prevent console popup flashes
            cmd = 'tasklist /FO CSV /NH'
            output = subprocess.check_output(cmd, shell=True, creationflags=0x08000000).decode('utf-8', errors='ignore').lower()
            return any(proc in output for proc in TARGET_GAME_PROCESSES)
        except Exception:
            # On check failure, default to True so overlay doesn't close accidentally
            return True

    def check_game_process(self):
        """Periodically checks if game is active; closes overlay if game has closed."""
        now = time.time()
        if now - self.last_process_check_time >= PROCESS_CHECK_INTERVAL:
            self.last_process_check_time = now
            if not self.is_game_running():
                print("Game process non-existent. Exiting HP Overlay...")
                self.root.destroy()
                sys.exit(0)

    def log_error(self, message):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(ERROR_LOG_FILE, "a") as f:
                f.write(f"\n--- {timestamp} ---\n{message}\n{traceback.format_exc()}\n")
        except: pass

    def display_error_on_canvas(self, message=None):
        self.canvas.delete("all")
        msg = message if message else self.error_message
        if self.error_start_time:
            remaining = max(0, math.ceil(RESTART_DELAY - (time.time() - self.error_start_time)))
            msg += f"\nRestarting in {remaining}s..."
        self.canvas.create_text(detected_user_res_X // 2, detected_user_res_Y // 2,
                                text=msg, fill="red", font=("Arial", 24, "bold"), justify="center")

    def restart_script(self):
        python = sys.executable
        os.execv(python, [python] + sys.argv)

    def load_assets(self):
        try: self.bg_img_pil = Image.open(BACKGROUND_PATH)
        except: self.bg_img_pil = None
        
        try: self.left_cap_pil = Image.open(LEFT_CAP_PATH)
        except: self.left_cap_pil = None

        try: self.right_cap_pil = Image.open(RIGHT_CAP_PATH)
        except: self.right_cap_pil = None

        self.fill_imgs_pil = {k: Image.open(v) for k, v in FILL_PATHS.items() if os.path.exists(v)}
        self.boss_icons_pil = {}
        if os.path.exists(BOSS_ICONS_DIR):
            for filename in os.listdir(BOSS_ICONS_DIR):
                if filename.lower().endswith(('.png', '.jpg')):
                    try: self.boss_icons_pil[os.path.splitext(filename)[0]] = Image.open(os.path.join(BOSS_ICONS_DIR, filename))
                    except: pass

    def load_settings(self):
        settings = {}
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f: settings = json.load(f)
        except: pass
        self.current_font_file = settings.get("font_file", DEFAULT_FONT_FILE)
        self.current_font_size = settings.get("font_size", DEFAULT_FONT_SIZE)
        path = os.path.join(FONTS_DIR, self.current_font_file)
        try: self.pil_font = ImageFont.truetype(path, self.current_font_size)
        except: self.pil_font = ImageFont.load_default()
        self.current_text_color = tuple(settings.get("text_color", DEFAULT_TEXT_COLOR))
        self.current_text_outline_width = settings.get("text_outline_width", DEFAULT_TEXT_OUTLINE_WIDTH)
        self.current_text_outline_color = tuple(settings.get("text_outline_color", DEFAULT_TEXT_OUTLINE_COLOR))
        self.use_text_background = settings.get("use_text_background", DEFAULT_USE_TEXT_BACKGROUND)
        self.show_mouseover_only = settings.get("show_mouseover_only", False)

    def load_game_data(self):
        try:
            with open(MONSTER_FILE, "r") as f:
                content = f.read().strip()
                return json.loads(content) if content else {"Monsters": [], "TargetedMonsterIndex": None}
        except: return {"Monsters": [], "TargetedMonsterIndex": None}

    def get_scale(self, distance):
        if not ENABLE_SCALING: return 1.0
        if distance <= SCALE_NEAR_DIST: return SCALE_NEAR
        if distance >= SCALE_FAR_DIST: return SCALE_FAR
        t = (distance - SCALE_NEAR_DIST) / (SCALE_FAR_DIST - SCALE_NEAR_DIST)
        return SCALE_NEAR + t * (SCALE_FAR - SCALE_NEAR)

    def _get_tk_image(self, pil_source, target_width, target_height, opacity=255):
        if pil_source is None: return None
        resized = pil_source.resize((max(1, int(target_width)), max(1, int(target_height))), Image.LANCZOS).convert('RGBA')
        if opacity < 255:
            alpha = resized.split()[-1].point(lambda p: p * (opacity / 255.0))
            resized.putalpha(alpha)
        tk_img = ImageTk.PhotoImage(resized)
        self.tk_image_references.append(tk_img)
        return tk_img

    def render_text(self, text, color=None, opacity=255, size_mult=1.0):
        clr = color if color is not None else self.current_text_color
        out_clr = self.current_text_outline_color
        out_w = max(1, int(self.current_text_outline_width * size_mult))
        
        font_size = max(8, int(self.current_font_size * size_mult))
        try:
            path = os.path.join(FONTS_DIR, self.current_font_file)
            font = ImageFont.truetype(path, font_size)
        except:
            font = ImageFont.load_default()

        bbox = font.getbbox(text)
        w, h = bbox[2] - bbox[0] + out_w * 2, bbox[3] - bbox[1] + out_w * 2
        img = Image.new("RGBA", (w + 8, h + 4), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        tx, ty = out_w - bbox[0] + 4, out_w - bbox[1] + 2
        for ox in range(-out_w, out_w + 1):
            for oy in range(-out_w, out_w + 1):
                if ox or oy: draw.text((tx+ox, ty+oy), text, font=font, fill=out_clr)
        draw.text((tx, ty), text, font=font, fill=clr)
        if opacity < 255:
            alpha = img.split()[-1].point(lambda p: p * (opacity / 255.0))
            img.putalpha(alpha)
        tk_img = ImageTk.PhotoImage(img)
        self.tk_image_references.append(tk_img)
        return tk_img

    def draw_bar(self, mon, bar_opacity=255, text_opacity=255, override_x=None, override_y=None, is_highlighted=False, size_mult=1.0):
        hp, fhp = mon.get("HP", 0), mon.get("FullHP", 1)
        name = mon.get("Name", "Unknown")
        dist = mon.get("Distance", 1000)
        
        x = override_x if override_x is not None else mon.get("ScreenX", 0)
        y = override_y if override_y is not None else mon.get("ScreenY", 0)
        
        scale = self.get_scale(dist) * size_mult
        is_boss = any(name.startswith(p) for p in BOSS_PREFIXES)
        
        bw = int(mon.get("BarSize", 200) * scale * (1.2 if is_boss else 1))
        bh = int(BASE_HEIGHT * scale)
        cw, rw = int(LEFT_CAP_WIDTH * scale), int(RIGHT_CAP_WIDTH * scale)
        fh = int(FILL_HEIGHT * scale)
        bx, by = int(x - bw // 2), int(y - bh)
        mw = bw - (cw + rw)

        if bar_opacity > 0:
            if is_highlighted:
                self.canvas.create_rectangle(bx-2, by-2, bx+bw+2, by+bh+2, outline="white", width=2)

            bg_tk = self._get_tk_image(self.bg_img_pil, bw, bh, bar_opacity)
            self.canvas.create_image(bx, by, anchor="nw", image=bg_tk)
            
            if self.left_cap_pil and cw > 0:
                l_cap_tk = self._get_tk_image(self.left_cap_pil, cw, bh, bar_opacity)
                self.canvas.create_image(bx, by, anchor="nw", image=l_cap_tk)

            if self.right_cap_pil and rw > 0:
                r_cap_tk = self._get_tk_image(self.right_cap_pil, rw, bh, bar_opacity)
                self.canvas.create_image(bx + bw - rw, by, anchor="nw", image=r_cap_tk)

            dmg = mon.get("LastHitDamage", 0)
            if dmg > 0:
                prev_ratio = max(0, min(1, (hp + dmg) / fhp))
                hit_fill = self.fill_imgs_pil.get("crit" if mon.get("IsCrit") else "hit")
                hit_w = int(prev_ratio * mw)
                if hit_w > 0:
                    self.canvas.create_image(bx + cw, by + (bh-fh)//2, anchor="nw", image=self._get_tk_image(hit_fill, hit_w, fh, bar_opacity))

            ratio = max(0, min(1, hp / fhp))
            fill_key = "boss" if is_boss else ("50" if ratio <= 0.5 else ("75" if ratio <= 0.75 else "default"))
            fill_w = int(ratio * mw)
            if fill_w > 0:
                fill_img = self.fill_imgs_pil.get(fill_key)
                self.canvas.create_image(bx + cw, by + (bh-fh)//2, anchor="nw", image=self._get_tk_image(fill_img, fill_w, fh, bar_opacity))

            if is_boss:
                for b_name, b_img in self.boss_icons_pil.items():
                    if name.startswith(b_name):
                        isize = int(32 * scale)
                        self.canvas.create_image(bx - 5, by + bh//2, anchor="e", image=self._get_tk_image(b_img, isize, isize, bar_opacity))
                        break

            t_color = (255, 255, 0, 255) if is_highlighted else None
            self.canvas.create_image(x, by - 4, anchor="s", image=self.render_text(f"{name} {hp}/{fhp}", color=t_color, opacity=bar_opacity, size_mult=size_mult))

        if hp <= 0:
            self.canvas.create_image(x, by + bh//2, anchor="center", image=self.render_text("Dead", DEFAULT_DEAD_TEXT_COLOR, text_opacity, size_mult=size_mult))

    def update_bars(self, game_data):
        try:
            self.canvas.delete("all")
            self.tk_image_references = []
            now = time.time()
            monsters = game_data.get("Monsters", [])
            targeted_idx = game_data.get("TargetedMonsterIndex")
            
            for m in monsters:
                idx = m['Index']
                if m['HP'] <= 0 and idx not in self.fading_monsters and idx not in self.permanently_hidden_monsters:
                    self.fading_monsters[idx] = {'start': now, 'data': m}

            world_monsters = []
            close_monsters = []
            for m in monsters:
                if m['HP'] > 0:
                    # Skip non-targeted monsters if mouseover-only setting is enabled
                    if self.show_mouseover_only and m['Index'] != targeted_idx:
                        continue
                    if m.get("Distance", 9999) < CLOSE_RANGE_THRESHOLD:
                        close_monsters.append(m)
                    else:
                        world_monsters.append(m)

            close_monsters.sort(key=lambda m: m.get("Distance", 0), reverse=True)

            # Draw World Monsters normally
            for m in world_monsters:
                self.draw_bar(m, is_highlighted=(m['Index'] == targeted_idx))

            # Grid Logic for Close Monsters (Max 3 per column, dynamic scaling)
            num_close = len(close_monsters)
            if num_close > 0:
                cols = math.ceil(num_close / CLOSE_STACK_MAX_PER_COL)
                
                dynamic_shrink = 1.0
                if cols > 2: dynamic_shrink = 0.7
                elif cols > 1: dynamic_shrink = 0.85
                
                current_grid_scale = GRID_BASE_SCALE * dynamic_shrink
                current_spacing_x = CLOSE_STACK_SPACING_X * dynamic_shrink
                current_spacing_y = CLOSE_STACK_SPACING_Y * dynamic_shrink

                for i, m in enumerate(close_monsters):
                    col_idx = i // CLOSE_STACK_MAX_PER_COL 
                    row_idx = i % CLOSE_STACK_MAX_PER_COL
                    
                    grid_x = CLOSE_STACK_START_X + (col_idx - (cols-1)/2) * current_spacing_x
                    grid_y = CLOSE_STACK_START_Y + (row_idx * current_spacing_y)
                    
                    self.draw_bar(m, override_x=grid_x, override_y=grid_y, 
                                  is_highlighted=(m['Index'] == targeted_idx), 
                                  size_mult=current_grid_scale)

            for idx in list(self.fading_monsters.keys()):
                f = self.fading_monsters[idx]
                elapsed = now - f['start']
                if elapsed > FADE_OUT_DURATION:
                    self.permanently_hidden_monsters.add(idx)
                    del self.fading_monsters[idx]
                else:
                    # Respect mouseover-only setting on fading dead bars as well
                    if self.show_mouseover_only and idx != targeted_idx:
                        continue
                    opacity = int(255 * (1 - (elapsed / FADE_OUT_DURATION)))
                    self.draw_bar(f['data'], bar_opacity=0, text_opacity=opacity)

        except Exception as e:
            self.log_error(f"Render Error: {e}")
            self.error_occurred, self.error_start_time = True, time.time()
            self.display_error_on_canvas()

    def update_loop(self):
        if self.error_occurred:
            if time.time() - self.error_start_time >= RESTART_DELAY: self.restart_script()
            else: self.display_error_on_canvas(); self.root.after(200, self.update_loop)
            return
        try:
            self.check_game_process()
            self.load_settings()
            self.update_bars(self.load_game_data())
        except Exception as e:
            self.log_error(f"Loop Error: {e}")
            self.error_occurred, self.error_start_time = True, time.time()
        self.root.after(UPDATE_INTERVAL, self.update_loop)

if __name__ == "__main__":
    root = tk.Tk()
    OverlayApp(root)
    root.mainloop()