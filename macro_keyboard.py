"""
MacroBoard Pro - Ultimate Edition (Scroll Fixed + Import/Export + i18n)
ต้องการ: pip install keyboard pyautogui
รันด้วย Admin / Run as Administrator
"""

import sys, os, json, ctypes, threading, time
import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox

# ── Admin & Deps ──────────────────────────────────────────────────────────────
def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

def run_as_admin():
    if sys.platform == "win32" and not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit(0)

run_as_admin()

try:
    import keyboard, pyautogui
    pyautogui.FAILSAFE = False
    HOTKEY_OK = True
except ImportError:
    HOTKEY_OK = False

# ── Config & Settings ─────────────────────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "macros.json")
SETTING_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

def load_settings():
    if os.path.exists(SETTING_FILE):
        try:
            with open(SETTING_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {"lang": "th"}

def save_settings(s):
    with open(SETTING_FILE, "w", encoding="utf-8") as f: json.dump(s, f)

def load_macros():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE,"r",encoding="utf-8") as f: return json.load(f)
        except: pass
    return []

def save_macros(macros):
    with open(CONFIG_FILE,"w",encoding="utf-8") as f:
        json.dump(macros, f, ensure_ascii=False, indent=2)

# ── DirectInput Hardware Level (แก้อาการเกมไม่รับปุ่ม) ─────────────────────────
SendInput = ctypes.windll.user32.SendInput
PUL = ctypes.POINTER(ctypes.c_ulong)

class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort), ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong), ("dwExtraInfo", PUL)]
class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong), ("wParamL", ctypes.c_short), ("wParamH", ctypes.c_ushort)]
class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong), ("time",ctypes.c_ulong), ("dwExtraInfo", PUL)]
class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput), ("mi", MouseInput), ("hi", HardwareInput)]
class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", Input_I)]

HW_KEYS = {
    'up': (0xC8, True), 'left': (0xCB, True), 'right': (0xCD, True), 'down': (0xD0, True),
    'space': (0x39, False), 'shift': (0x2A, False), 'ctrl': (0x1D, False), 'alt': (0x38, False),
    'enter': (0x1C, False), 'esc': (0x01, False), 'tab': (0x0F, False), 'backspace': (0x0E, False),
    'q': (0x10, False), 'w': (0x11, False), 'e': (0x12, False), 'r': (0x13, False),
    't': (0x14, False), 'y': (0x15, False), 'u': (0x16, False), 'i': (0x17, False),
    'o': (0x18, False), 'p': (0x19, False), 'a': (0x1E, False), 's': (0x1F, False),
    'd': (0x20, False), 'f': (0x21, False), 'g': (0x22, False), 'h': (0x23, False),
    'j': (0x24, False), 'k': (0x25, False), 'l': (0x26, False), 'z': (0x2C, False),
    'x': (0x2D, False), 'c': (0x2E, False), 'v': (0x2F, False), 'b': (0x30, False),
    'n': (0x31, False), 'm': (0x32, False),
    '1': (0x02, False), '2': (0x03, False), '3': (0x04, False), '4': (0x05, False),
    '5': (0x06, False), '6': (0x07, False), '7': (0x08, False), '8': (0x09, False),
    '9': (0x0A, False), '0': (0x0B, False)
}

def hw_press(key_name):
    k = key_name.lower()
    if k in HW_KEYS:
        code, is_ext = HW_KEYS[k]
        flags = 0x0008 | (0x0001 if is_ext else 0)
        ii = Input_I()
        ii.ki = KeyBdInput(0, code, flags, 0, ctypes.pointer(ctypes.c_ulong(0)))
        x = Input(ctypes.c_ulong(1), ii)
        SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
        return True
    return False

def hw_release(key_name):
    k = key_name.lower()
    if k in HW_KEYS:
        code, is_ext = HW_KEYS[k]
        flags = 0x0008 | 0x0002 | (0x0001 if is_ext else 0)
        ii = Input_I()
        ii.ki = KeyBdInput(0, code, flags, 0, ctypes.pointer(ctypes.c_ulong(0)))
        x = Input(ctypes.c_ulong(1), ii)
        SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
        return True
    return False

# ── Executor ──────────────────────────────────────────────────────────────────
def execute_macro(macro, check_active_func=None):
    if not macro.get("enabled", True): return
    
    t = macro.get("type", "text")
    pm = macro.get("play_mode", "once")
    active_keys = set()
    
    def do_normal_action():
        action = macro.get("action", "")
        if t == "text": pyautogui.typewrite(action.replace("{date}", time.strftime("%Y-%m-%d")), interval=0.02)
        elif t == "hotkey":
            for c in [x.strip() for x in action.split(",")]: keyboard.send(c); time.sleep(0.05)
        elif t == "cmd": os.startfile(action) if sys.platform=="win32" else os.system(action)

    def run_sequence():
        if t != "sequence":
            do_normal_action()
            return True
        seq = macro.get("sequence", [])
        for step in seq:
            if check_active_func and not check_active_func(): return False
            k = step.get("key", "").lower()
            if k:
                try:
                    if step.get("state") == "down":
                        if not hw_press(k): keyboard.press(k)
                        active_keys.add(k)
                    else:
                        if not hw_release(k): keyboard.release(k)
                        active_keys.discard(k)
                except Exception as e: print(f"Key err: {e}")

            d = step.get("delay", 0) / 1000.0
            if d > 0:
                slept = 0
                while slept < d:
                    if check_active_func and not check_active_func(): return False
                    time.sleep(0.01); slept += 0.01
        return True

    try:
        global_delay = macro.get("delay", 0) / 1000.0
        if global_delay > 0 and t != "sequence":
            time.sleep(global_delay)

        single_run = (check_active_func is None)
        
        if single_run or pm == "once":
            run_sequence()
        elif pm == "n_times":
            loops = max(1, macro.get("loop_count", 1))
            for _ in range(loops):
                if not run_sequence(): break
                if t != "sequence": time.sleep(0.05)
        elif pm in ("hold", "toggle"):
            while check_active_func and check_active_func():
                if not run_sequence(): break
                if t != "sequence": time.sleep(0.05)
                
    except Exception as e: pass
    finally:
        for k in list(active_keys):
            try: 
                if not hw_release(k): keyboard.release(k)
            except: pass

# ── Hotkey manager ────────────────────────────────────────────────────────────
class HotkeyManager:
    def __init__(self):
        self._entries = {}
        self._hook    = None
        self._physical_keys = {}
        self._toggle_states = {}

    def _rebuild(self):
        if self._hook:
            try: keyboard.unhook(self._hook)
            except: pass
            self._hook = None
        if not self._entries or not HOTKEY_OK: return
        snap = dict(self._entries)

        def on_event(event):
            if not event.name: return True
            name = event.name.lower()
            if event.event_type == keyboard.KEY_UP:
                for mid, entry in snap.items():
                    if name == entry["trigger"]: self._physical_keys[mid] = False
                return True
            if event.event_type == keyboard.KEY_DOWN:
                for mid, entry in snap.items():
                    if name == entry["trigger"] and all(keyboard.is_pressed(m) for m in entry["mods"]):
                        pm = entry["macro"].get("play_mode", "once")
                        if self._physical_keys.get(mid, False): return False 
                        self._physical_keys[mid] = True
                        if pm == "toggle":
                            current = self._toggle_states.get(mid, False)
                            self._toggle_states[mid] = not current
                            if self._toggle_states[mid]:
                                threading.Thread(target=execute_macro, args=(entry["macro"], lambda m=mid: self._toggle_states.get(m, False)), daemon=True).start()
                        else:
                            threading.Thread(target=execute_macro, args=(entry["macro"], lambda m=mid: self._physical_keys.get(m, False)), daemon=True).start()
                        return False
                return True
        self._hook = keyboard.hook(on_event, suppress=True)

    def register(self, m):
        self._entries.pop(m["id"], None)
        hk = m.get("hotkey", "").strip()
        if hk and m.get("enabled", True):
            parts = [p.strip() for p in hk.split('+')]
            self._entries[m["id"]] = {"macro": m, "trigger": parts[-1].lower(), "mods": [p.lower() for p in parts[:-1]]}
        self._rebuild()

    def unregister(self, mid):
        if mid in self._entries: del self._entries[mid]
        self._rebuild()

    def reload_all(self, macros):
        self._entries.clear(); self._physical_keys.clear(); self._toggle_states.clear()
        for m in macros: self.register(m)

def _rgb(h): return tuple(int(h.lstrip("#")[i:i+2],16) for i in (0,2,4))
def darken(h, f=0.18):
    r,g,b = _rgb(h)
    return "#{:02x}{:02x}{:02x}".format(max(0,int(r*(1-f))), max(0,int(g*(1-f))), max(0,int(b*(1-f))))

# ─────────────────────────────────────────────────────────────────────────────
#  App UI
# ─────────────────────────────────────────────────────────────────────────────
class MacroApp(tk.Tk):
    BG, SIDE, PANEL, CARD, SEL, ACCENT = "#12121e", "#191928", "#1d1d2e", "#23233a", "#2c2c48", "#ff002b"
    TEXT, SUB, GREEN, GREENS, YELLOW, BORDER = "#ffffff", "#64748b", "#21ff72", "#40c46e", "#ffb535", "#373750"
    FB, FS, FT = ("Segoe UI", 10), ("Segoe UI", 9), ("Segoe UI", 11, "bold")

    def __init__(self):
        super().__init__()
        self.sys_settings = load_settings()
        self.macros = load_macros()
        self.hkm = HotkeyManager()
        self._next_id = max((m["id"] for m in self.macros), default=0) + 1
        self._sel_id, self._edit_new, self._edit_vars, self._cards = None, False, {}, {}
        self._build_ui()
        self.hkm.reload_all(self.macros)
        self._refresh_list()
        self._show_empty()
        
        # ── Global Scroll Fix ──
        # แทนที่จะ bind แย่งกันแบบเดิม เราจะ bind ที่ root แล้วให้มันคำนวณเอง
        self.bind_all("<MouseWheel>", self._on_mousewheel)
        
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        if not HOTKEY_OK: self._set_status(self.T("ติดตั้ง pip install keyboard pyautogui", "Install keyboard pyautogui"), warn=True)

    def T(self, th, en):
        """ระบบแปลภาษา (Returns English if lang is 'en', else Thai)"""
        return en if self.sys_settings.get("lang") == "en" else th

    def _on_mousewheel(self, e):
        """ตัวจัดการ Scroll อัจฉริยะ (ดูว่าเมาส์ชี้อยู่ฝั่งไหน ก็เลื่อนฝั่งนั้น)"""
        w = self.winfo_containing(e.x_root, e.y_root)
        if not w: return
        try:
            curr = w
            while curr:
                # ถ้าเมาส์อยู่ฝั่งซ้าย (รายการมาโคร)
                if curr == self._cv:
                    self._cv.yview_scroll(int(-1*(e.delta/120)), "units")
                    return
                # ถ้าเมาส์อยู่ฝั่งขวา (หน้าตั้งค่า/แก้ไข)
                if hasattr(self, '_ec') and curr == self._ec:
                    self._ec.yview_scroll(int(-1*(e.delta/120)), "units")
                    return
                curr = curr.master
        except: pass

    def _build_ui(self):
        self.title("MacroBoard Pro"); self.geometry("860x560"); self.minsize(720, 450); self.configure(bg=self.BG); 
        # เอา iconbitmap ออกเผื่อเครื่องที่ไม่มีไฟล์ icon.ico จะได้ไม่บัค
        try: self.iconbitmap("icon.ico") 
        except: pass
        
        tk.Frame(self, bg=self.ACCENT, height=3).pack(fill="x")
        
        # ── Top Bar ──
        tb = tk.Frame(self, bg=self.BG, pady=8); tb.pack(fill="x", padx=14)
        tk.Label(tb, text="⌨  MacroBoard", font=("Segoe UI",14,"bold"), bg=self.BG, fg=self.TEXT).pack(side="left")
        b = tk.Frame(tb, bg=self.BG); b.pack(side="right")
        ok = is_admin()
        tk.Label(b, text="🔒 Admin" if ok else "⚠ No Admin", font=self.FS, bg=self.BG, fg=self.GREEN if ok else self.YELLOW).pack(side="left", padx=6)
        tk.Frame(b, bg=self.BORDER, width=1, height=14).pack(side="left", pady=3)
        ok2 = HOTKEY_OK
        tk.Label(b, text="● ON" if ok2 else "● OFF", font=self.FS, bg=self.BG, fg=self.GREEN if ok2 else self.ACCENT).pack(side="left", padx=6)

        split = tk.Frame(self, bg=self.BG); split.pack(fill="both", expand=True, padx=10, pady=(0,6))
        split.columnconfigure(1, weight=1); split.rowconfigure(0, weight=1)

        # ── Sidebar ──
        left = tk.Frame(split, bg=self.SIDE, width=220, highlightthickness=1, highlightbackground=self.BORDER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0,8)); left.grid_propagate(False)
        left.rowconfigure(1, weight=1); left.columnconfigure(0, weight=1)

        lhdr = tk.Frame(left, bg=self.SIDE, pady=7); lhdr.grid(row=0, column=0, sticky="ew", padx=8)
        tk.Label(lhdr, text=self.T("รายการมาโคร", "MACROS"), font=("Segoe UI",8,"bold"), bg=self.SIDE, fg=self.SUB).pack(side="left")
        tk.Button(lhdr, text="＋", font=("Segoe UI",11,"bold"), bg=self.ACCENT, fg="#fff", relief="flat", width=2, cursor="hand2", command=self._do_add).pack(side="right")

        lw = tk.Frame(left, bg=self.SIDE); lw.grid(row=1, column=0, sticky="nsew")
        lw.rowconfigure(0, weight=1); lw.columnconfigure(0, weight=1)
        self._cv = tk.Canvas(lw, bg=self.SIDE, bd=0, highlightthickness=0); self._cv.grid(row=0, column=0, sticky="nsew")
        sb = tk.Scrollbar(lw, orient="vertical", command=self._cv.yview, bg=self.SIDE, troughcolor=self.SIDE, relief="flat", width=5)
        sb.grid(row=0, column=1, sticky="ns"); self._cv.configure(yscrollcommand=sb.set)
        self._cf = tk.Frame(self._cv, bg=self.SIDE); self._cw = self._cv.create_window((0,0), window=self._cf, anchor="nw")
        
        self._cf.bind("<Configure>", lambda e: self._cv.configure(scrollregion=self._cv.bbox("all")))
        self._cv.bind("<Configure>", lambda e: self._cv.itemconfig(self._cw, width=e.width))
        # Note: ตัดการผูก bind_all <MouseWheel> ออกไปรวมที่ root ตรงบรรทัดที่ 319 แล้ว

        # ── Settings Button ──
        sbar = tk.Frame(left, bg=self.SIDE, pady=5); sbar.grid(row=2, column=0, sticky="ew")
        tk.Button(sbar, text=self.T("⚙ ตั้งค่า (Settings)", "⚙ Settings"), font=self.FS, bg=self.CARD, fg=self.TEXT, relief="flat", cursor="hand2", command=self._show_settings).pack(fill="x", padx=10, pady=5)

        # ── Right Panel ──
        self._right = tk.Frame(split, bg=self.PANEL, highlightthickness=1, highlightbackground=self.BORDER)
        self._right.grid(row=0, column=1, sticky="nsew"); self._right.rowconfigure(0, weight=1); self._right.columnconfigure(0, weight=1)

        self._pane_empty = self._mk_empty()
        self._pane_view = self._mk_view()
        self._pane_edit = self._mk_edit()
        self._pane_settings = self._mk_settings()
        
        for p in (self._pane_empty, self._pane_view, self._pane_edit, self._pane_settings): 
            p.grid(row=0, column=0, sticky="nsew")

        self._svar = tk.StringVar(value=f"  {self.T('พร้อมใช้งาน', 'Ready')}")
        self._slbl = tk.Label(self, textvariable=self._svar, font=self.FS, bg=self.BG, fg=self.SUB, anchor="w")
        self._slbl.pack(fill="x", padx=14, pady=(0,5))

    def _mk_empty(self):
        f = tk.Frame(self._right, bg=self.PANEL)
        tk.Label(f, text="⌨", font=("Segoe UI",40), bg=self.PANEL, fg=self.BORDER).place(relx=.5, rely=.38, anchor="c")
        tk.Label(f, text=self.T("เลือก Macro หรือกด ＋ เพิ่มใหม่", "Select a Macro or press ＋"), font=self.FS, bg=self.PANEL, fg=self.SUB).place(relx=.5, rely=.53, anchor="c")
        return f

    def _mk_settings(self):
        f = tk.Frame(self._right, bg=self.PANEL)
        ehdr = tk.Frame(f, bg=self.CARD, pady=7); ehdr.pack(fill="x")
        tk.Label(ehdr, text=self.T("⚙  ตั้งค่าระบบ (Settings)", "⚙  Settings"), font=self.FT, bg=self.CARD, fg=self.TEXT).pack(side="left", padx=14)
        
        c = tk.Frame(f, bg=self.PANEL, pady=20, padx=20); c.pack(fill="both", expand=True)
        
        # Language Set
        tk.Label(c, text=self.T("🌐 ภาษา (Language)", "🌐 Language"), font=self.FB, bg=self.PANEL, fg=self.SUB).grid(row=0, column=0, sticky="w", pady=(0, 10))
        lf = tk.Frame(c, bg=self.PANEL); lf.grid(row=0, column=1, sticky="w", pady=(0, 10), padx=20)
        self._lang_var = tk.StringVar(value=self.sys_settings.get("lang", "th"))
        tk.Radiobutton(lf, text="ภาษาไทย", variable=self._lang_var, value="th", font=self.FS, bg=self.PANEL, fg=self.TEXT, selectcolor=self.CARD, command=self._apply_lang).pack(side="left", padx=(0,10))
        tk.Radiobutton(lf, text="English", variable=self._lang_var, value="en", font=self.FS, bg=self.PANEL, fg=self.TEXT, selectcolor=self.CARD, command=self._apply_lang).pack(side="left")
        
        # Import/Export Set
        tk.Label(c, text=self.T("📂 จัดการข้อมูล (Data)", "📂 Manage Data"), font=self.FB, bg=self.PANEL, fg=self.SUB).grid(row=1, column=0, sticky="w", pady=20)
        bf = tk.Frame(c, bg=self.PANEL); bf.grid(row=1, column=1, sticky="w", pady=20, padx=20)
        tk.Button(bf, text=self.T("📥 นำเข้า (Import)", "📥 Import Macros"), font=self.FS, bg=self.CARD, fg="#47a0ff", relief="flat", padx=15, pady=5, cursor="hand2", command=self._do_import).pack(side="left", padx=(0, 10))
        tk.Button(bf, text=self.T("📤 ส่งออก (Export All)", "📤 Export All Macros"), font=self.FS, bg=self.CARD, fg=self.YELLOW, relief="flat", padx=15, pady=5, cursor="hand2", command=self._do_export).pack(side="left")
        
        return f

    def _mk_view(self):
        f = tk.Frame(self._right, bg=self.PANEL); f.columnconfigure(0, weight=1); f.rowconfigure(2, weight=1)
        self._v_bar = tk.Frame(f, bg=self.ACCENT, height=5); self._v_bar.grid(row=0, column=0, sticky="ew")
        
        th = tk.Frame(f, bg=self.PANEL); th.grid(row=1, column=0, sticky="ew", padx=14, pady=(10,4)); th.columnconfigure(0, weight=1)
        self._v_name = tk.Label(th, text="", font=("Segoe UI",13,"bold"), bg=self.PANEL, fg=self.TEXT, anchor="w")
        self._v_name.grid(row=0, column=0, sticky="w")
        
        br = tk.Frame(th, bg=self.PANEL); br.grid(row=0, column=1, sticky="e")
        self._v_tog = tk.Button(br, text=self.T("⏸ ปิด", "⏸ Off"), font=self.FS, bg=self.CARD, fg=self.YELLOW, relief="flat", padx=8, pady=4, cursor="hand2", command=self._do_toggle)
        self._v_tog.pack(side="left", padx=2)
        tk.Button(br, text=self.T("✎ แก้ไข", "✎ Edit"), font=self.FS, bg=self.CARD, fg="#47a0ff", relief="flat", padx=8, pady=4, cursor="hand2", command=self._do_edit).pack(side="left", padx=2)
        tk.Button(br, text=self.T("🗑 ลบ", "🗑 Del"), font=self.FS, bg=self.CARD, fg=self.ACCENT, relief="flat", padx=8, pady=4, cursor="hand2", command=self._do_delete).pack(side="left", padx=2)
        
        info = tk.Frame(f, bg=self.PANEL); info.grid(row=2, column=0, sticky="nsew", padx=14, pady=6); info.columnconfigure(2, weight=1)
        self._vr = {}
        labels = [("hotkey","Hotkey"), ("type",self.T("ประเภท","Type")), ("action_or_loop",self.T("รูปแบบ (Mode)","Mode")), ("delay",self.T("ดีเลย์","Delay")), ("status",self.T("สถานะ","Status"))]
        for i,(k,l) in enumerate(labels):
            tk.Label(info, text=l, font=self.FS, bg=self.PANEL, fg=self.SUB, width=14, anchor="w").grid(row=i, column=0, sticky="w", pady=4)
            v = tk.Label(info, text="", font=self.FB, bg=self.PANEL, fg=self.TEXT, anchor="w", wraplength=380)
            v.grid(row=i, column=2, sticky="ew", pady=4); self._vr[k] = v

        bot = tk.Frame(f, bg=self.CARD); bot.grid(row=3, column=0, sticky="ew")
        tk.Button(bot, text=self.T("▶  ทดสอบ", "▶  Test Macro"), font=self.FB, bg=self.GREENS, fg="#fff", relief="flat", padx=14, pady=7, cursor="hand2", command=self._do_test).pack(side="left", padx=10, pady=7)
        tk.Button(bot, text=self.T("⟳ รีโหลด", "⟳ Reload"), font=self.FS, bg=self.CARD, fg=self.SUB, relief="flat", padx=10, pady=7, cursor="hand2", command=self._do_reload).pack(side="right", padx=10, pady=7)
        return f

    def _mk_edit(self):
        outer = tk.Frame(self._right, bg=self.PANEL); outer.columnconfigure(0, weight=1); outer.rowconfigure(1, weight=1)
        ehdr = tk.Frame(outer, bg=self.CARD, pady=7); ehdr.grid(row=0, column=0, sticky="ew"); ehdr.columnconfigure(1, weight=1)
        self._e_title = tk.Label(ehdr, text="✎", font=self.FT, bg=self.CARD, fg=self.TEXT, anchor="w"); self._e_title.grid(row=0, column=0, padx=14, sticky="w")
        tk.Button(ehdr, text=self.T("← ยกเลิก", "← Cancel"), font=self.FS, bg=self.CARD, fg=self.SUB, relief="flat", padx=10, pady=3, cursor="hand2", command=self._cancel_edit).grid(row=0, column=2, padx=10, sticky="e")
        
        fw = tk.Frame(outer, bg=self.PANEL); fw.grid(row=1, column=0, sticky="nsew"); fw.rowconfigure(0, weight=1); fw.columnconfigure(0, weight=1)
        self._ec = tk.Canvas(fw, bg=self.PANEL, bd=0, highlightthickness=0); self._ec.grid(row=0, column=0, sticky="nsew")
        esb = tk.Scrollbar(fw, orient="vertical", command=self._ec.yview, bg=self.PANEL, troughcolor=self.PANEL, width=5, relief="flat")
        esb.grid(row=0, column=1, sticky="ns"); self._ec.configure(yscrollcommand=esb.set)
        self._ef = tk.Frame(self._ec, bg=self.PANEL); self._ew = self._ec.create_window((0,0), window=self._ef, anchor="nw")
        
        self._ef.bind("<Configure>", lambda e: self._ec.configure(scrollregion=self._ec.bbox("all")))
        self._ec.bind("<Configure>", lambda e: self._ec.itemconfig(self._ew, width=e.width) if self._ec.find_all() else None)
        # Note: ตัดการผูก bind_all <MouseWheel> ออกไปรวมที่ root ตรงบรรทัดที่ 319 เช่นกัน
        
        sbar = tk.Frame(outer, bg=self.CARD); sbar.grid(row=2, column=0, sticky="ew")
        tk.Button(sbar, text=self.T("💾  บันทึก", "💾  Save"), font=self.FB, bg=self.ACCENT, fg="#fff", relief="flat", padx=18, pady=8, cursor="hand2", command=self._do_save).pack(side="right", padx=10, pady=6)
        return outer

    def _show_empty(self): self._pane_empty.tkraise()
    
    def _show_settings(self):
        self._sel_id = None
        self._refresh_list()
        self._pane_settings.tkraise()

    def _apply_lang(self):
        new_lang = self._lang_var.get()
        if self.sys_settings.get("lang") != new_lang:
            self.sys_settings["lang"] = new_lang
            save_settings(self.sys_settings)
            for w in self.winfo_children(): w.destroy()
            self._build_ui()
            self.hkm.reload_all(self.macros)
            self._refresh_list()
            self._pane_settings.tkraise()

    def _do_import(self):
        p = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if p:
            try:
                with open(p, "r", encoding="utf-8") as f: imported = json.load(f)
                if isinstance(imported, dict): imported = [imported]
                for m in imported:
                    self._next_id += 1
                    m["id"] = self._next_id
                    self.macros.append(m)
                save_macros(self.macros)
                self.hkm.reload_all(self.macros)
                self._refresh_list()
                self._set_status(self.T("นำเข้าข้อมูลเรียบร้อย ✅", "Import Successful ✅"))
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _do_export(self):
        if not self.macros:
            messagebox.showwarning("Empty", self.T("ไม่มีข้อมูลให้ส่งออก", "No macros to export."))
            return
        p = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")], initialfile="MacroBoard_Backup.json")
        if p:
            try:
                with open(p, "w", encoding="utf-8") as f: json.dump(self.macros, f, ensure_ascii=False, indent=2)
                self._set_status(self.T("ส่งออกไฟล์เรียบร้อย ✅", "Export Successful ✅"))
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _show_edit(self, macro, is_new=False):
        self._edit_new = is_new
        self._e_title.config(text=self.T("✎ เพิ่ม Macro ใหม่", "✎ Add New Macro") if is_new else self.T("✎ แก้ไข Macro", "✎ Edit Macro"))
        self._build_form(macro)
        self._pane_edit.tkraise()

    def _show_view(self, m):
        enabled = m.get("enabled", True)
        color = m.get("color", self.ACCENT)
        self._v_bar.config(bg=color); self._v_name.config(text=m["name"], fg=color)
        self._vr["hotkey"].config(text=m.get("hotkey","—"), fg="#a0c4ff")
        
        t = m.get("type","text")
        self._vr["type"].config(text={"text":self.T("📝 ข้อความ", "📝 Text"), "hotkey":self.T("⌨ ปุ่ม", "⌨ Hotkey"), "cmd":"🖥 CMD", "sequence":"⏱ Sequence"}.get(t, t))
        
        pm = m.get("play_mode", "once")
        pms = {"once": self.T("รอบเดียว", "Play Once"), "hold": self.T("วนลูปตอนกดค้าง", "Hold Loop"), "toggle": self.T("เปิด/ปิดสลับกัน", "Toggle Loop"), "n_times": self.T(f"วน {m.get('loop_count',1)} รอบ", f"Loop {m.get('loop_count',1)} Times")}
        
        if t == "sequence":
            self._vr["action_or_loop"].config(text=f"{pms.get(pm, pm)}", fg=self.YELLOW)
            self._vr["delay"].config(text=self.T("(ตั้งค่าแยกในแต่ละปุ่ม)", "(Set per sequence key)"), fg=self.SUB)
        else:
            act = m.get("action","")
            self._vr["action_or_loop"].config(text=f"[{pms.get(pm, pm)}] {act[:40]}...", fg=self.TEXT)
            d = m.get("delay", 0)
            self._vr["delay"].config(text=f"⏱ {d} ms" if d else "0 ms", fg=self.YELLOW if d else self.SUB)
            
        self._vr["status"].config(text=self.T("✅ เปิดใช้งาน", "✅ Enabled") if enabled else self.T("⛔ ปิดใช้งาน", "⛔ Disabled"), fg=self.GREEN if enabled else self.ACCENT)
        self._v_tog.config(text=self.T("⏸ ปิด", "⏸ Turn Off") if enabled else self.T("▶ เปิด", "▶ Turn On"), fg=self.YELLOW if enabled else self.GREEN)
        self._pane_view.tkraise()

    def _build_form(self, macro):
        for w in self._ef.winfo_children(): w.destroy()
        self._edit_vars = {"_ref": macro}; f = self._ef; f.columnconfigure(1, weight=1); r = [0]
        
        def lbl(t): ro=r[0]; r[0]+=1; tk.Label(f, text=t, font=self.FS, bg=self.PANEL, fg=self.SUB, anchor="w").grid(row=ro, column=0, sticky="nw", padx=(14,8), pady=(10,2)); return ro
        def erow(l, k, val):
            ro = lbl(l); var = tk.StringVar(value=val)
            tk.Entry(f, textvariable=var, font=self.FB, bg=self.CARD, fg=self.TEXT, insertbackground=self.TEXT, relief="flat", bd=6).grid(row=ro, column=1, sticky="ew", padx=(0,14), pady=(10,2))
            self._edit_vars[k] = var

        erow(self.T("ชื่อ Macro", "Macro Name"), "name", macro.get("name",""))
        erow("Hotkey", "hotkey", macro.get("hotkey",""))

        mro = lbl(self.T("รูปแบบลูป", "Loop Mode"))
        mb = tk.Frame(f, bg=self.PANEL); mb.grid(row=mro, column=1, sticky="ew", padx=(0,14), pady=(10,2))
        pm_var = tk.StringVar(value=macro.get("play_mode", "once")); self._edit_vars["play_mode"] = pm_var
        opts = [(self.T("รอบเดียว", "Once"),"once"), (self.T("กดค้าง (Hold)", "Hold"),"hold"), (self.T("เปิด/ปิด (Toggle)", "Toggle"),"toggle")]
        for t, v in opts: tk.Radiobutton(mb, text=t, variable=pm_var, value=v, font=self.FS, bg=self.PANEL, fg=self.TEXT, selectcolor=self.CARD, activebackground=self.PANEL, activeforeground=self.TEXT).pack(side="left", padx=(0,8))
        tk.Radiobutton(mb, text=self.T("จำนวนรอบ", "Times"), variable=pm_var, value="n_times", font=self.FS, bg=self.PANEL, fg=self.TEXT, selectcolor=self.CARD).pack(side="left")
        lcv = tk.IntVar(value=macro.get("loop_count", 1)); self._edit_vars["loop_count"] = lcv
        tk.Spinbox(mb, from_=1, to=999, textvariable=lcv, width=4, font=self.FB, bg=self.CARD, fg=self.TEXT, relief="flat", buttonbackground=self.CARD).pack(side="left", padx=(4,0))

        tro = lbl(self.T("ประเภท", "Type"))
        type_var = tk.StringVar(value=macro.get("type","sequence")); self._edit_vars["type"] = type_var
        ttk.Combobox(f, textvariable=type_var, values=["text","hotkey","cmd","sequence"], font=self.FB, state="readonly", width=12).grid(row=tro, column=1, sticky="w", padx=(0,14), pady=(10,2))
        
        albl = tk.Label(f, text="Action", font=self.FS, bg=self.PANEL, fg=self.SUB, anchor="nw")
        aro = r[0]; r[0]+=1; albl.grid(row=aro, column=0, sticky="nw", padx=(14,8), pady=(10,2))
        ac = tk.Frame(f, bg=self.PANEL); ac.grid(row=aro, column=1, sticky="nsew", padx=(0,14), pady=(10,2))
        ac.columnconfigure(0, weight=1); f.rowconfigure(aro, weight=1)
        
        av = [macro.get("action","")]; cur = []; ga = [None]
        self._edit_vars["_seq"] = [s.copy() for s in macro.get("sequence", [])]

        def clr():
            for w in cur:
                try: w.destroy()
                except: pass
            cur.clear()

        def bld_text():
            clr(); albl.config(text=self.T("ข้อความ", "Text"))
            t = tk.Text(ac, font=self.FB, bg=self.CARD, fg=self.TEXT, insertbackground=self.TEXT, relief="flat", bd=6, height=4, wrap="word"); t.insert("1.0", av[0]); t.grid(row=0, column=0, sticky="ew")
            cur.append(t); return lambda: t.get("1.0","end-1c").strip()
        
        def bld_hk():
            clr(); albl.config(text=self.T("ปุ่ม (คั่นด้วย , )", "Keys (comma sep)"))
            var = tk.StringVar(value=av[0])
            e = tk.Entry(ac, textvariable=var, font=self.FB, bg=self.CARD, fg=self.TEXT, insertbackground=self.TEXT, relief="flat", bd=6); e.grid(row=0, column=0, sticky="ew")
            cur.append(e); return lambda: var.get().strip()
            
        def bld_cmd():
            clr(); albl.config(text=self.T("คำสั่ง/ไฟล์", "Cmd/File"))
            var = tk.StringVar(value=av[0])
            rf = tk.Frame(ac, bg=self.PANEL); rf.grid(row=0, column=0, sticky="ew"); rf.columnconfigure(0, weight=1)
            tk.Entry(rf, textvariable=var, font=self.FB, bg=self.CARD, fg=self.TEXT, insertbackground=self.TEXT, relief="flat", bd=6).grid(row=0, column=0, sticky="ew")
            tk.Button(rf, text="📂", font=self.FS, bg=self.CARD, fg=self.SUB, relief="flat", padx=8, pady=4, cursor="hand2", command=lambda: (p:=filedialog.askopenfilename()) and var.set(p)).grid(row=0, column=1, padx=(4,0))
            cur.append(rf); return lambda: var.get().strip()

        def bld_seq():
            clr(); albl.config(text=self.T("ลำดับ (Sequence)", "Sequence"))
            seq_frame = tk.Frame(ac, bg=self.CARD, bd=1, relief="flat"); seq_frame.grid(row=0, column=0, sticky="nsew")
            
            def render_seq():
                for w in seq_frame.winfo_children(): w.destroy()
                c_seq = self._edit_vars["_seq"]
                if not c_seq: tk.Label(seq_frame, text=self.T("ยังไม่มีปุ่มกด กดเพิ่ม หรือ Record", "No sequence yet. Click Add or Record."), font=self.FS, bg=self.CARD, fg=self.SUB, pady=10).pack()
                
                for i, step in enumerate(c_seq):
                    rw = tk.Frame(seq_frame, bg=self.CARD, pady=2, padx=4); rw.pack(fill="x")
                    tk.Label(rw, text=f"{i+1}.", font=self.FB, bg=self.CARD, fg=self.SUB, width=2).pack(side="left")
                    
                    kvar = tk.StringVar(value=step.get("key","").upper()[:8])
                    kbtn = tk.Button(rw, textvariable=kvar, width=8, font=("Consolas", 10, "bold"), bg=self.PANEL, fg=self.TEXT, relief="flat", cursor="hand2")
                    
                    def assign_key(idx=i, btn=kbtn, var=kvar):
                        btn.config(text=self.T("[ กด... ]", "[ Press ]"), bg=self.YELLOW, fg=self.BG)
                        h_ref = []
                        def _hook(e):
                            if e.event_type == keyboard.KEY_DOWN and e.name:
                                kn = e.name.lower()
                                c_seq[idx]["key"] = kn
                                btn.after(0, lambda: var.set(kn.upper()[:8]))
                                btn.after(0, lambda: btn.config(bg=self.PANEL, fg=self.TEXT))
                                try: keyboard.unhook(h_ref[0])
                                except: pass
                                return False
                            return True
                        h_ref.append(keyboard.hook(_hook, suppress=True))
                        
                    kbtn.config(command=assign_key); kbtn.pack(side="left", padx=2)
                    
                    is_dn = step.get("state") == "down"
                    sbtn = tk.Button(rw, text="↓ Down" if is_dn else "↑ Up", width=6, font=self.FS, bg=self.BG if is_dn else self.PANEL, fg=self.TEXT if is_dn else self.SUB, relief="flat", cursor="hand2")
                    def tog(idx=i, btn=sbtn):
                        ns = "up" if c_seq[idx].get("state")=="down" else "down"; c_seq[idx]["state"] = ns
                        btn.config(text="↓ Down" if ns=="down" else "↑ Up", bg=self.BG if ns=="down" else self.PANEL, fg=self.TEXT if ns=="down" else self.SUB)
                    sbtn.config(command=tog); sbtn.pack(side="left", padx=2)
                    
                    tk.Label(rw, text="Delay(ms):", font=self.FS, bg=self.CARD, fg=self.SUB).pack(side="left", padx=(8,2))
                    dvar = tk.StringVar(value=str(step.get("delay",0)))
                    dent = tk.Entry(rw, textvariable=dvar, width=5, font=self.FB, bg=self.PANEL, fg=self.YELLOW, relief="flat", justify="center"); dent.pack(side="left")
                    dent.bind("<KeyRelease>", lambda e, idx=i, v=dvar: c_seq[idx].update({"delay": int(v.get() or 0) if str(v.get()).isdigit() else 0}))
                    tk.Button(rw, text="✕", font=self.FS, bg=self.CARD, fg=self.ACCENT, relief="flat", command=lambda idx=i: (c_seq.pop(idx), render_seq()), cursor="hand2").pack(side="right")

                bc = tk.Frame(seq_frame, bg=self.CARD, pady=4); bc.pack(fill="x")
                tk.Button(bc, text=self.T("＋ เพิ่มบรรทัด", "＋ Add Row"), font=self.FS, bg=self.PANEL, fg=self.TEXT, relief="flat", cursor="hand2", command=lambda: (c_seq.append({"key":"left","state":"down","delay":25}), render_seq())).pack(side="left", padx=4)
                
                rec_btn = tk.Button(bc, text="🔴 Record", font=self.FS, bg="#b91c1c", fg="#fff", relief="flat", cursor="hand2")
                rec_state = [False, []]; rec_hook_ref = []
                def do_rec():
                    if not rec_state[0]:
                        rec_state[0] = True; rec_state[1] = []; rec_btn.config(text="⏹ Stop", bg=self.YELLOW, fg=self.BG)
                        h = keyboard.hook(lambda e: rec_state[1].append((e.event_type, e.name.lower(), time.time())) if e.name and e.name.lower()!="esc" else None)
                        rec_hook_ref.append(h)
                    else:
                        rec_state[0] = False
                        if rec_hook_ref:
                            try: keyboard.unhook(rec_hook_ref.pop())
                            except: pass
                        rec_btn.config(text="🔴 Record", bg="#b91c1c", fg="#fff")
                        if rec_state[1]:
                            c_seq.clear()
                            events = rec_state[1]
                            for idx in range(len(events)):
                                et, kn, ts = events[idx]
                                if idx < len(events) - 1: delay_ms = int((events[idx+1][2] - ts) * 1000)
                                else: delay_ms = 0
                                c_seq.append({"key": kn, "state": "down" if et==keyboard.KEY_DOWN else "up", "delay": delay_ms})
                            render_seq()
                rec_btn.config(command=do_rec); rec_btn.pack(side="left")

            render_seq(); cur.append(seq_frame); return lambda: ""

        def on_t(*_):
            t = type_var.get()
            if t=="text": ga[0]=bld_text()
            elif t=="hotkey": ga[0]=bld_hk()
            elif t=="cmd": ga[0]=bld_cmd()
            else: ga[0]=bld_seq()
        type_var.trace_add("write", on_t); on_t()

        dro = lbl("Global Delay")
        dv2 = tk.IntVar(value=int(macro.get("delay",0))); self._edit_vars["delay"] = dv2
        tk.Spinbox(f, from_=0, to=10000, increment=50, textvariable=dv2, width=6, font=self.FB, bg=self.CARD, fg=self.TEXT, insertbackground=self.TEXT, relief="flat", bd=4, buttonbackground=self.CARD).grid(row=dro, column=1, sticky="w", padx=(0,14), pady=(10,2))

        cro = lbl(self.T("สีปุ่ม", "Button Color"))
        cv = [macro.get("color","#4f8ef7")]; cf = tk.Frame(f, bg=self.PANEL); cf.grid(row=cro, column=1, sticky="w", padx=(0,14), pady=(10,2))
        cp = tk.Label(cf, bg=cv[0], width=3, height=1, relief="flat"); cp.pack(side="left", padx=(0,6))
        tk.Button(cf, text=self.T("เลือกสี", "Pick Color"), font=self.FS, bg=self.CARD, fg=self.TEXT, relief="flat", padx=8, pady=3, cursor="hand2", command=lambda: (c:=colorchooser.askcolor(color=cv[0]))[1] and (cv.__setitem__(0,c[1]), cp.config(bg=c[1]))).pack(side="left")
        self._edit_vars["_color"] = cv
        self._edit_vars["_ga"] = ga

    def _set_status(self, msg, warn=False):
        self._svar.set(f"  {msg}"); self._slbl.config(fg=self.YELLOW if warn else self.SUB)

    def _get_m(self, mid=None): return next((m for m in self.macros if m["id"]==(mid or self._sel_id)), None)
    
    def _do_add(self):
        self._next_id += 1
        self._show_edit({"id":self._next_id, "name":f"Macro {self._next_id}", "hotkey":"F10", "type":"sequence", "color":"#4f8ef7", "enabled":True, "delay":0}, is_new=True)
    
    def _do_edit(self):
        m = self._get_m(); m and self._show_edit(m)
        
    def _cancel_edit(self):
        m = self._get_m(); m and self._show_view(m) or self._show_empty()
    
    def _do_save(self):
        ev, m = self._edit_vars, self._edit_vars["_ref"]
        m["name"] = ev["name"].get().strip() or "Macro"
        m["hotkey"] = ev["hotkey"].get().strip()
        m["type"] = ev["type"].get()
        m["action"] = ev["_ga"][0]() if ev["_ga"][0] else ""
        m["color"] = ev["_color"][0]
        m["play_mode"] = ev["play_mode"].get()
        try: m["loop_count"] = max(1, int(ev["loop_count"].get()))
        except: m["loop_count"] = 1
        try: m["delay"] = max(0, int(ev["delay"].get()))
        except: m["delay"] = 0
        if m["type"] == "sequence": m["sequence"] = ev.get("_seq", [])
        
        if self._edit_new: self.macros.append(m); self._sel_id = m["id"]; self._edit_new = False
        save_macros(self.macros); self.hkm.register(m); self._refresh_list(m["id"]); self._show_view(m)
        self._set_status(self.T(f"บันทึก '{m['name']}' แล้ว ✅", f"Saved '{m['name']}' ✅"))

    def _do_delete(self):
        m = self._get_m()
        if m and messagebox.askyesno(self.T("ลบ", "Delete"), self.T(f"ลบ '{m['name']}' ?", f"Delete '{m['name']}' ?")):
            self.hkm.unregister(m["id"]); self.macros = [x for x in self.macros if x["id"]!=m["id"]]
            self._sel_id = None; save_macros(self.macros); self._refresh_list(); self._show_empty()
            self._set_status(self.T(f"ลบ '{m['name']}' แล้ว", f"Deleted '{m['name']}'"))

    def _do_toggle(self):
        m = self._get_m();
        if m:
            m["enabled"] = not m.get("enabled", True)
            save_macros(self.macros); self.hkm.register(m); self._refresh_list(m["id"]); self._show_view(m)
            self._set_status(self.T("เปิด" if m["enabled"] else "ปิด", "Enabled" if m["enabled"] else "Disabled") + f" '{m['name']}'")

    def _do_test(self):
        m = self._get_m();
        if m:
            self._set_status(self.T(f"ทดสอบ '{m['name']}'...", f"Testing '{m['name']}'...")); threading.Thread(target=execute_macro, args=(m,), daemon=True).start()

    def _do_reload(self):
        self.hkm.reload_all(self.macros); self._set_status(self.T("รีโหลด Hotkeys แล้ว ✅", "Hotkeys Reloaded ✅"))

    def _refresh_list(self, sel_id=None):
        for w in self._cf.winfo_children(): w.destroy()
        self._cv.update_idletasks()
        self._cv.configure(scrollregion=self._cv.bbox("all")) # อัพเดทกล่องให้รับค่าเพื่อดึงแถบ scroll
        self._cards.clear()
        if sel_id: self._sel_id = sel_id
        for m in self.macros:
            is_sel = m["id"] == self._sel_id; enabled = m.get("enabled", True)
            c = m.get("color", self.ACCENT); bg = self.SEL if is_sel else self.SIDE
            card = tk.Frame(self._cf, bg=bg, cursor="hand2"); card.pack(fill="x", pady=1); card.columnconfigure(1, weight=1)
            tk.Frame(card, bg=c if enabled else self.BORDER, width=4).grid(row=0, column=0, rowspan=2, sticky="ns", padx=(2,0))
            tk.Label(card, text=m["name"], font=("Segoe UI",10,"bold"), bg=bg, fg=self.TEXT if enabled else self.SUB, anchor="w").grid(row=0, column=1, sticky="ew", padx=(8,4), pady=(6,1))
            bot = tk.Frame(card, bg=bg); bot.grid(row=1, column=1, sticky="ew", padx=(8,6), pady=(0,6))
            tk.Label(bot, text=m.get("hotkey","—"), font=("Consolas",8,"bold"), bg=darken(c, 0.55) if enabled else self.CARD, fg=c if enabled else self.SUB, padx=5, pady=1).pack(side="left")
            for w in [card]+list(card.winfo_children())+list(bot.winfo_children()): 
                w.bind("<Button-1>", lambda e, mid=m["id"]: self._select(mid))
                w.bind("<Double-Button-1>", lambda e, mid=m["id"]: (self._select(mid), self._do_edit()))
            self._cards[m["id"]] = card
        if not self.macros: self._show_empty()

    def _select(self, mid):
        old = self._sel_id; self._sel_id = mid
        for xid in [old, mid]:
            card = self._cards.get(xid)
            if card:
                bg = self.SEL if xid==mid else self.SIDE; card.config(bg=bg)
                for c in card.winfo_children(): c.config(bg=bg) if "Label" in str(type(c)) and c.cget("text") not in (self._get_m(xid).get("hotkey","—"),"●","○") else None
        m = self._get_m(mid)
        if m: self._show_view(m)

    def _on_close(self): save_macros(self.macros); save_settings(self.sys_settings); self.destroy()

if __name__ == "__main__": MacroApp().mainloop()