import os, json, time, threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pyautogui, keyboard

try:
    from PIL import ImageGrab
except ImportError:
    pass

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

AMK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "amk_scripts.json")
SETTING_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

def load_settings():
    if os.path.exists(SETTING_FILE):
        try:
            with open(SETTING_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {"lang": "th"}

def save_settings(s):
    with open(SETTING_FILE, "w", encoding="utf-8") as f: json.dump(s, f)

def load_scripts():
    if os.path.exists(AMK_FILE):
        try:
            with open(AMK_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return []

def save_scripts(scripts):
    with open(AMK_FILE, "w", encoding="utf-8") as f:
        json.dump(scripts, f, ensure_ascii=False, indent=2)

class OverlaySpy(tk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.attributes("-fullscreen", True)
        self.attributes("-alpha", 0.3)
        self.attributes("-topmost", True)
        self.config(cursor="crosshair")
        self.bind("<Button-1>", self.on_click)
        self.bind("<Escape>", lambda e: self.destroy())
        
        lbl = tk.Label(self, text="คลิกซ้ายที่หน้าจอเพื่อดึงพิกัด X, Y (กด ESC เพื่อยกเลิก)", font=("Segoe UI", 24, "bold"), fg="white", bg="black")
        lbl.pack(expand=True)
        self.wm_attributes("-transparentcolor", "black")

    def on_click(self, event):
        x, y = event.x_root, event.y_root
        self.destroy()
        if self.callback: self.callback(x, y)

class SnippingTool(tk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.attributes("-fullscreen", True)
        self.attributes("-alpha", 0.3)
        self.attributes("-topmost", True)
        self.config(cursor="crosshair")
        
        self.start_x = None
        self.start_y = None
        self.rect = None
        
        self.canvas = tk.Canvas(self, cursor="crosshair", bg="black")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Escape>", lambda e: self.destroy())

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2, fill="black")

    def on_drag(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        x1 = min(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        x2 = max(self.start_x, event.x)
        y2 = max(self.start_y, event.y)
        self.withdraw()
        self.update()
        if x2 - x1 > 5 and y2 - y1 > 5:
            try:
                img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
                out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
                if not os.path.exists(out_dir): os.makedirs(out_dir)
                filename = os.path.join(out_dir, f"capture_{int(time.time())}.png")
                img.save(filename)
                if self.callback: self.callback(filename)
            except Exception as e:
                print("Capture error:", e)
        self.destroy()

class AMKExecutor:
    def __init__(self):
        self.running = False
        self.paused = False
        self.current_step = 0
        self.thread = None

    def _sleep(self, ms):
        end = time.time() + (ms / 1000.0)
        while time.time() < end and self.running:
            time.sleep(0.01)

    def run_script(self, script, update_ui_cb=None):
        self.running = True
        self.paused = False
        self.thread = threading.Thread(target=self._execute, args=(script, update_ui_cb), daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

    def _execute(self, script, update_ui_cb):
        steps = script.get("steps", [])
        loop_mode = script.get("loop_mode", "times")
        loop_count = script.get("loop_count", 1)

        loop = 0
        while self.running:
            if loop_mode == "times" and loop >= loop_count:
                break
                
            self.current_step = 0
            while self.current_step < len(steps):
                if not self.running: break
                while self.paused and self.running: time.sleep(0.1)
                
                step = steps[self.current_step]
                if update_ui_cb: update_ui_cb(self.current_step)
                
                try: self._run_step(step, steps)
                except Exception as e: print(f"Error at step {self.current_step}: {e}")
                
                self.current_step += 1
                self._sleep(10)
                
            loop += 1
                
        self.running = False
        if update_ui_cb: update_ui_cb(-1)

    def _run_step(self, step, steps):
        cmd = step.get("cmd")
        delay_after = step.get("delay_after", 0)

        if cmd == "delay":
            self._sleep(step.get("ms", 1000))
        elif cmd == "mouse_move":
            duration = 0.5 if step.get("tween", False) else 0
            relative = step.get("relative", False)
            if relative:
                pyautogui.move(step.get("x", 0), step.get("y", 0), duration=duration, tween=pyautogui.easeInOutQuad)
            else:
                pyautogui.moveTo(step.get("x", 0), step.get("y", 0), duration=duration, tween=pyautogui.easeInOutQuad)
        elif cmd == "mouse_click":
            pyautogui.click(button=step.get("btn", "left"))
        elif cmd == "key_press":
            keyboard.send(step.get("key", "enter"))
        elif cmd == "type_text":
            text = step.get("text", "")
            try:
                import pyperclip
                pyperclip.copy(text)
                self._sleep(50)
                keyboard.send("ctrl+v" if os.name == "nt" else "command+v")
            except ImportError:
                keyboard.write(text, delay=0.02)
            
        elif cmd == "find_image":
            img = step.get("image", "")
            if os.path.exists(img):
                confidence = step.get("confidence", 80) / 100.0
                timeout = step.get("timeout", 0)
                timeout_action = step.get("timeout_action", "stop")
                action = step.get("action", "click")
                move_corner = step.get("move_corner", False)
                tween = step.get("tween", False)

                start_time = time.time()
                found_loc = None

                if move_corner:
                    pyautogui.moveTo(0, 0, duration=0)

                while self.running:
                    try:
                        loc = pyautogui.locateCenterOnScreen(img, confidence=confidence) if OPENCV_AVAILABLE else pyautogui.locateCenterOnScreen(img)
                        if loc:
                            found_loc = loc
                            break
                    except:
                        pass
                    
                    if timeout > 0 and (time.time() - start_time) > timeout:
                        break
                    else:
                        self._sleep(100)

                if found_loc and self.running:
                    duration = 0.5 if tween else 0
                    if action == "click": 
                        pyautogui.moveTo(found_loc, duration=duration, tween=pyautogui.easeInOutQuad)
                        pyautogui.click()
                    elif action == "move": 
                        pyautogui.moveTo(found_loc, duration=duration, tween=pyautogui.easeInOutQuad)
                    elif action == "double_click": 
                        pyautogui.moveTo(found_loc, duration=duration, tween=pyautogui.easeInOutQuad)
                        pyautogui.doubleClick()
                    elif action == "right_click": 
                        pyautogui.moveTo(found_loc, duration=duration, tween=pyautogui.easeInOutQuad)
                        pyautogui.rightClick()
                else:
                    if timeout_action == "stop" and not found_loc:
                        self.running = False

        elif cmd == "if_image":
            img = step.get("image", "")
            confidence = step.get("confidence", 80) / 100.0
            found = False
            if os.path.exists(img):
                try:
                    loc = pyautogui.locateCenterOnScreen(img, confidence=confidence) if OPENCV_AVAILABLE else pyautogui.locateCenterOnScreen(img)
                    if loc: found = True
                except: pass
            
            if not found:
                nested = 0
                while self.current_step + 1 < len(steps):
                    next_step = steps[self.current_step + 1]
                    ncmd = next_step.get("cmd")
                    if ncmd == "if_image": nested += 1
                    elif ncmd == "end_if":
                        if nested == 0: break
                        nested -= 1
                    elif ncmd == "else":
                        if nested == 0: break
                    self.current_step += 1

        elif cmd == "else":
            nested = 0
            while self.current_step + 1 < len(steps):
                next_step = steps[self.current_step + 1]
                ncmd = next_step.get("cmd")
                if ncmd == "if_image": nested += 1
                elif ncmd == "end_if":
                    if nested == 0: break
                    nested -= 1
                self.current_step += 1
                
        elif cmd == "end_if":
            pass

        if delay_after > 0:
            self._sleep(delay_after)

class AMKFrame(tk.Frame):
    def __init__(self, parent, bg_color, panel_color, card_color, text_color, accent_color, sub_color):
        super().__init__(parent, bg=bg_color)
        self.BG = bg_color; self.PANEL = panel_color; self.CARD = card_color; self.TEXT = text_color
        self.ACCENT = accent_color; self.SUB = sub_color
        self.sys_settings = load_settings()
        self.scripts = load_scripts()
        self.sel_script = None
        self.executor = AMKExecutor()
        self.hk_hook = None
        self._build_ui()
        self._refresh_list()
        self._bind_hotkeys()

    def T(self, th, en):
        return en if self.sys_settings.get("lang") == "en" else th

    def _apply_lang(self):
        new_lang = self._lang_var.get()
        if self.sys_settings.get("lang") != new_lang:
            self.sys_settings["lang"] = new_lang
            save_settings(self.sys_settings)
            for w in self.winfo_children(): w.destroy()
            self._build_ui()
            self._refresh_list()

    def _do_import(self):
        p = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if p:
            try:
                with open(p, "r", encoding="utf-8") as f: imported = json.load(f)
                if isinstance(imported, dict): imported = [imported]
                nid = max([s.get("id", 0) for s in self.scripts] + [0])
                for m in imported:
                    nid += 1
                    m["id"] = nid
                    self.scripts.append(m)
                save_scripts(self.scripts)
                self._refresh_list()
                messagebox.showinfo("Import", self.T("นำเข้าข้อมูลเรียบร้อย ✅", "Import Successful ✅"))
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _do_export(self):
        if not self.scripts:
            messagebox.showwarning("Empty", self.T("ไม่มีข้อมูลให้ส่งออก", "No scripts to export."))
            return
        p = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")], initialfile="AMK_Backup.json")
        if p:
            try:
                with open(p, "w", encoding="utf-8") as f: json.dump(self.scripts, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("Export", self.T("ส่งออกไฟล์เรียบร้อย ✅", "Export Successful ✅"))
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _show_settings(self):
        self.sel_script = None
        self._refresh_list()
        self._settings_view.tkraise()

    def _bind_hotkeys(self):
        def on_event(e):
            if e.event_type == keyboard.KEY_DOWN and e.name:
                kn = e.name.lower()
                for s in self.scripts:
                    if s.get("hotkey", "").lower() == kn and s.get("enabled", True):
                        if not self.executor.running:
                            self.executor.run_script(s, self._update_pointer)
                        else:
                            self.executor.stop()
        self.hk_hook = keyboard.hook(on_event)

    def _build_ui(self):
        left = tk.Frame(self, bg=self.PANEL, width=200, highlightthickness=1, highlightbackground="#373750")
        left.pack(side="left", fill="y", padx=10, pady=10)
        left.pack_propagate(False)
        
        tk.Label(left, text="🤖 Action Scripts", font=("Segoe UI", 12, "bold"), bg=self.PANEL, fg=self.TEXT).pack(pady=10)
        tk.Button(left, text=self.T("＋ สร้างใหม่", "＋ New Script"), bg=self.ACCENT, fg="white", relief="flat", command=self._new_script).pack(fill="x", padx=10)
        
        self.listbox = tk.Listbox(left, bg=self.CARD, fg=self.TEXT, selectbackground=self.ACCENT, relief="flat", bd=0, highlightthickness=0)
        self.listbox.pack(fill="both", expand=True, padx=10, pady=10)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        sbar = tk.Frame(left, bg=self.PANEL, pady=5)
        sbar.pack(fill="x", side="bottom")
        tk.Button(sbar, text=self.T("⚙ ตั้งค่า (Settings)", "⚙ Settings"), font=("Segoe UI", 9), bg=self.CARD, fg=self.TEXT, relief="flat", cursor="hand2", command=self._show_settings).pack(fill="x", padx=10, pady=5)

        self._right_container = tk.Frame(self, bg=self.BG)
        self._right_container.pack(side="right", fill="both", expand=True, pady=10, padx=(0,10))

        self._main_view = tk.Frame(self._right_container, bg=self.BG)
        self._main_view.place(relwidth=1, relheight=1)

        self.hdr = tk.Frame(self._main_view, bg=self.PANEL, pady=10, padx=10)
        self.hdr.pack(fill="x", pady=(0, 10))
        
        tk.Label(self.hdr, text=self.T("ชื่อ:", "Name:"), bg=self.PANEL, fg=self.SUB).pack(side="left")
        self.v_name = tk.StringVar()
        en_name = tk.Entry(self.hdr, textvariable=self.v_name, bg=self.CARD, fg=self.TEXT, relief="flat")
        en_name.pack(side="left", padx=5)
        en_name.bind("<KeyRelease>", self._save_auto)

        tk.Label(self.hdr, text="Hotkey:", bg=self.PANEL, fg=self.SUB).pack(side="left", padx=(10,0))
        self.v_hk = tk.StringVar()
        en_hk = tk.Entry(self.hdr, textvariable=self.v_hk, width=8, bg=self.CARD, fg=self.TEXT, relief="flat")
        en_hk.pack(side="left", padx=5)
        en_hk.bind("<KeyRelease>", self._save_auto)
        
        tk.Label(self.hdr, text=self.T("วนลูป:", "Loop:"), bg=self.PANEL, fg=self.SUB).pack(side="left", padx=(10,0))
        self.v_loop_mode = tk.StringVar(value="times")
        cb_loop = ttk.Combobox(self.hdr, textvariable=self.v_loop_mode, values=["times", "infinite"], width=8, state="readonly")
        cb_loop.pack(side="left", padx=2)
        cb_loop.bind("<<ComboboxSelected>>", self._save_auto)

        self.v_loop = tk.IntVar(value=1)
        en_loop = tk.Entry(self.hdr, textvariable=self.v_loop, width=4, bg=self.CARD, fg=self.TEXT, relief="flat")
        en_loop.pack(side="left", padx=2)
        en_loop.bind("<KeyRelease>", self._save_auto)

        self.btn_play = tk.Button(self.hdr, text="▶ Play", bg="#21ff72", fg="black", relief="flat", font=("Segoe UI", 9, "bold"), command=self._play_stop)
        self.btn_play.pack(side="right", padx=5)
        
        tk.Button(self.hdr, text=self.T("🗑 ลบ", "🗑 Delete"), bg=self.CARD, fg="#ff002b", relief="flat", command=self._del_script).pack(side="right", padx=10)

        self.timeline_frame = tk.Frame(self._main_view, bg=self.CARD)
        self.timeline_frame.pack(fill="both", expand=True)
        
        tools = tk.Frame(self._main_view, bg=self.PANEL, pady=5)
        tools.pack(fill="x", pady=(10,0))
        
        cmds_1 = [
            ("⏱ Delay", lambda: self._add_step({"cmd": "delay", "ms": 1000})),
            ("🖱 Move", lambda: self._add_step({"cmd": "mouse_move", "x": 0, "y": 0, "relative": False, "tween": False})),
            ("🖱 Click", lambda: self._add_step({"cmd": "mouse_click", "btn": "left"})),
            ("⌨ Key", lambda: self._add_step({"cmd": "key_press", "key": "enter"})),
            ("📝 Text", lambda: self._add_step({"cmd": "type_text", "text": "Hello"})),
        ]
        cmds_2 = [
            ("🖼 Find Image", lambda: self._add_step({"cmd": "find_image", "image": "", "action": "click", "confidence": 80, "timeout": 0, "timeout_action": "stop", "move_corner": False})),
            ("🔀 If Image", lambda: self._add_step({"cmd": "if_image", "image": "", "confidence": 80})),
            ("➖ Else", lambda: self._add_step({"cmd": "else"})),
            ("🛑 End If", lambda: self._add_step({"cmd": "end_if"})),
        ]
        
        row1 = tk.Frame(tools, bg=self.PANEL)
        row1.pack(fill="x", pady=2)
        row2 = tk.Frame(tools, bg=self.PANEL)
        row2.pack(fill="x", pady=2)

        tk.Label(row1, text="Basic:", bg=self.PANEL, fg=self.SUB, font=("Segoe UI", 9, "bold"), width=10, anchor="w").pack(side="left", padx=10)
        for t, cmd in cmds_1:
            tk.Button(row1, text=t, bg=self.CARD, fg=self.TEXT, relief="flat", command=cmd).pack(side="left", padx=2)
        tk.Button(row1, text="🎯 Spy", bg="#ffb535", fg="black", relief="flat", font=("Segoe UI", 9, "bold"), command=self._spy_xy).pack(side="right", padx=10)

        tk.Label(row2, text="Logic:", bg=self.PANEL, fg=self.SUB, font=("Segoe UI", 9, "bold"), width=10, anchor="w").pack(side="left", padx=10)
        for t, cmd in cmds_2:
            tk.Button(row2, text=t, bg=self.CARD, fg=self.TEXT, relief="flat", command=cmd).pack(side="left", padx=2)

        self._settings_view = tk.Frame(self._right_container, bg=self.PANEL)
        self._settings_view.place(relwidth=1, relheight=1)
        ehdr = tk.Frame(self._settings_view, bg=self.CARD, pady=7)
        ehdr.pack(fill="x")
        tk.Label(ehdr, text=self.T("⚙  ตั้งค่าระบบ (Settings)", "⚙  Settings"), font=("Segoe UI", 11, "bold"), bg=self.CARD, fg=self.TEXT).pack(side="left", padx=14)
        
        c = tk.Frame(self._settings_view, bg=self.PANEL, pady=20, padx=20)
        c.pack(fill="both", expand=True)
        
        tk.Label(c, text=self.T("🌐 ภาษา (Language)", "🌐 Language"), font=("Segoe UI", 10, "bold"), bg=self.PANEL, fg=self.SUB).grid(row=0, column=0, sticky="w", pady=(0, 10))
        lf = tk.Frame(c, bg=self.PANEL)
        lf.grid(row=0, column=1, sticky="w", pady=(0, 10), padx=20)
        self._lang_var = tk.StringVar(value=self.sys_settings.get("lang", "th"))
        tk.Radiobutton(lf, text="ภาษาไทย", variable=self._lang_var, value="th", font=("Segoe UI", 9), bg=self.PANEL, fg=self.TEXT, selectcolor=self.CARD, command=self._apply_lang).pack(side="left", padx=(0,10))
        tk.Radiobutton(lf, text="English", variable=self._lang_var, value="en", font=("Segoe UI", 9), bg=self.PANEL, fg=self.TEXT, selectcolor=self.CARD, command=self._apply_lang).pack(side="left")
        
        tk.Label(c, text=self.T("📂 จัดการข้อมูล (Data)", "📂 Manage Data"), font=("Segoe UI", 10, "bold"), bg=self.PANEL, fg=self.SUB).grid(row=1, column=0, sticky="w", pady=20)
        bf = tk.Frame(c, bg=self.PANEL)
        bf.grid(row=1, column=1, sticky="w", pady=20, padx=20)
        tk.Button(bf, text=self.T("📥 นำเข้า (Import)", "📥 Import Scripts"), font=("Segoe UI", 9), bg=self.CARD, fg="#47a0ff", relief="flat", padx=15, pady=5, cursor="hand2", command=self._do_import).pack(side="left", padx=(0, 10))
        tk.Button(bf, text=self.T("📤 ส่งออก (Export All)", "📤 Export All Scripts"), font=("Segoe UI", 9), bg=self.CARD, fg="#ffb535", relief="flat", padx=15, pady=5, cursor="hand2", command=self._do_export).pack(side="left")

        self._main_view.tkraise()

    def _spy_xy(self):
        def cb(x, y):
            self._add_step({"cmd": "mouse_move", "x": x, "y": y})
        OverlaySpy(self.winfo_toplevel(), cb)

    def _snip_image(self, step, string_var):
        def cb(filepath):
            string_var.set(filepath)
            step["image"] = filepath
            self._save_auto()
        SnippingTool(self.winfo_toplevel(), cb)

    def _play_stop(self):
        if not self.sel_script: return
        if self.executor.running:
            self.executor.stop()
            self.btn_play.config(text="▶ Play", bg="#21ff72")
        else:
            self.btn_play.config(text="⏹ Stop", bg="#ff002b", fg="white")
            self.executor.run_script(self.sel_script, self._update_pointer)

    def _update_pointer(self, step_idx):
        try:
            for w in self.timeline_frame.winfo_children(): w.config(bg=self.CARD)
            if step_idx >= 0 and step_idx < len(self.timeline_frame.winfo_children()):
                self.timeline_frame.winfo_children()[step_idx].config(bg="#40c46e")
            if step_idx == -1:
                self.btn_play.config(text="▶ Play", bg="#21ff72", fg="black")
        except: pass

    def _new_script(self):
        nid = max([s.get("id", 0) for s in self.scripts] + [0]) + 1
        new_s = {"id": nid, "name": f"Action {nid}", "hotkey": "", "loop_mode": "times", "loop_count": 1, "enabled": True, "steps": []}
        self.scripts.append(new_s)
        self._refresh_list()
        self.listbox.selection_set(tk.END)
        self._on_select(None)

    def _del_script(self):
        if self.sel_script and messagebox.askyesno("Delete", "Delete this script?"):
            self.scripts.remove(self.sel_script)
            self.sel_script = None
            self._refresh_list()
            self._render_timeline()

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        for s in self.scripts:
            self.listbox.insert(tk.END, f"{s['name']} [{s.get('hotkey','-')}]")
        save_scripts(self.scripts)

    def _on_select(self, e):
        sel = self.listbox.curselection()
        if sel:
            self.sel_script = self.scripts[sel[0]]
            self.v_name.set(self.sel_script.get("name", ""))
            self.v_hk.set(self.sel_script.get("hotkey", ""))
            self.v_loop_mode.set(self.sel_script.get("loop_mode", "times"))
            self.v_loop.set(self.sel_script.get("loop_count", 1))
            self._render_timeline()
            self._main_view.tkraise()

    def _save_auto(self, e=None):
        if self.sel_script:
            self.sel_script["name"] = self.v_name.get()
            self.sel_script["hotkey"] = self.v_hk.get()
            self.sel_script["loop_mode"] = self.v_loop_mode.get()
            try: self.sel_script["loop_count"] = int(self.v_loop.get())
            except: pass
            save_scripts(self.scripts)
            idx = self.scripts.index(self.sel_script)
            self.listbox.delete(idx)
            self.listbox.insert(idx, f"{self.sel_script['name']} [{self.sel_script['hotkey']}]")
            self.listbox.selection_set(idx)

    def _add_step(self, step_data):
        if not self.sel_script: return
        self.sel_script["steps"].append(step_data)
        self._save_auto()
        self._render_timeline()

    def _del_step(self, idx):
        if self.sel_script:
            self.sel_script["steps"].pop(idx)
            self._save_auto()
            self._render_timeline()

    def _move_step(self, idx, dir):
        if not self.sel_script: return
        steps = self.sel_script["steps"]
        if 0 <= idx + dir < len(steps):
            steps[idx], steps[idx+dir] = steps[idx+dir], steps[idx]
            self._save_auto()
            self._render_timeline()

    def _render_timeline(self):
        for w in self.timeline_frame.winfo_children(): w.destroy()
        if not self.sel_script: return

        canvas = tk.Canvas(self.timeline_frame, bg=self.CARD, highlightthickness=0)
        sb = tk.Scrollbar(self.timeline_frame, orient="vertical", command=canvas.yview, bg=self.PANEL)
        sf = tk.Frame(canvas, bg=self.CARD)
        
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=sb.set)
        canvas.create_window((0,0), window=sf, anchor="nw", width=canvas.winfo_width())
        sf.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas.find_all()[0], width=e.width))

        for i, step in enumerate(self.sel_script["steps"]):
            self._build_step_row(sf, i, step)

    def _build_step_row(self, parent, idx, step):
        row = tk.Frame(parent, bg=self.CARD, pady=5, highlightthickness=1, highlightbackground=self.PANEL)
        row.pack(fill="x", padx=5, pady=2)
        
        cmd = step.get("cmd")
        tk.Label(row, text=f"{idx+1}.", bg=self.CARD, fg=self.SUB, width=3, anchor="n").pack(side="left", fill="y")
        
        if cmd == "delay":
            tk.Label(row, text="⏱ Delay", bg=self.CARD, fg="#47a0ff", font=("Segoe UI", 9, "bold")).pack(side="left", padx=5)
            v = tk.StringVar(value=str(step.get("ms", 1000)))
            e = tk.Entry(row, textvariable=v, width=8, bg=self.PANEL, fg=self.TEXT, relief="flat")
            e.pack(side="left")
            tk.Label(row, text="ms", bg=self.CARD, fg=self.SUB).pack(side="left")
            e.bind("<KeyRelease>", lambda ev, st=step, vr=v: st.update({"ms": int(vr.get()) if vr.get().isdigit() else 0}) or self._save_auto())
            
        elif cmd == "mouse_move":
            tk.Label(row, text="🖱 Move Mouse", bg=self.CARD, fg="#ffb535", font=("Segoe UI", 9, "bold")).pack(side="left", padx=5)
            tk.Label(row, text="X:", bg=self.CARD, fg=self.SUB).pack(side="left")
            vx = tk.StringVar(value=str(step.get("x", 0)))
            ex = tk.Entry(row, textvariable=vx, width=5, bg=self.PANEL, fg=self.TEXT, relief="flat"); ex.pack(side="left")
            ex.bind("<KeyRelease>", lambda ev, st=step, vr=vx: st.update({"x": int(vr.get()) if vr.get().isdigit() else 0}) or self._save_auto())
            
            tk.Label(row, text="Y:", bg=self.CARD, fg=self.SUB).pack(side="left", padx=(5,0))
            vy = tk.StringVar(value=str(step.get("y", 0)))
            ey = tk.Entry(row, textvariable=vy, width=5, bg=self.PANEL, fg=self.TEXT, relief="flat"); ey.pack(side="left")
            ey.bind("<KeyRelease>", lambda ev, st=step, vr=vy: st.update({"y": int(vr.get()) if vr.get().isdigit() else 0}) or self._save_auto())
            
            vrel = tk.BooleanVar(value=step.get("relative", False))
            ck_rel = tk.Checkbutton(row, text="Relative", bg=self.CARD, fg=self.SUB, selectcolor=self.PANEL, activebackground=self.CARD, activeforeground=self.SUB, variable=vrel, command=lambda st=step, vr=vrel: st.update({"relative": vr.get()}) or self._save_auto())
            ck_rel.pack(side="left", padx=5)

            vtween = tk.BooleanVar(value=step.get("tween", False))
            ck = tk.Checkbutton(row, text="Tween", bg=self.CARD, fg=self.SUB, selectcolor=self.PANEL, activebackground=self.CARD, activeforeground=self.SUB, variable=vtween, command=lambda st=step, vr=vtween: st.update({"tween": vr.get()}) or self._save_auto())
            ck.pack(side="left", padx=5)
            
        elif cmd == "mouse_click":
            tk.Label(row, text="🖱 Click", bg=self.CARD, fg="#ffb535", font=("Segoe UI", 9, "bold")).pack(side="left", padx=5)
            vbtn = tk.StringVar(value=step.get("btn", "left"))
            cb = ttk.Combobox(row, textvariable=vbtn, values=["left", "right", "middle"], width=6, state="readonly")
            cb.pack(side="left")
            cb.bind("<<ComboboxSelected>>", lambda ev, st=step, vr=vbtn: st.update({"btn": vr.get()}) or self._save_auto())
            
        elif cmd == "key_press":
            tk.Label(row, text="⌨ Press Key", bg=self.CARD, fg="#21ff72", font=("Segoe UI", 9, "bold")).pack(side="left", padx=5)
            vkey = tk.StringVar(value=step.get("key", "enter"))
            ek = tk.Entry(row, textvariable=vkey, width=10, bg=self.PANEL, fg=self.TEXT, relief="flat"); ek.pack(side="left")
            ek.bind("<KeyRelease>", lambda ev, st=step, vr=vkey: st.update({"key": vr.get()}) or self._save_auto())
            
        elif cmd == "type_text":
            tk.Label(row, text="📝 Type Text", bg=self.CARD, fg="#21ff72", font=("Segoe UI", 9, "bold")).pack(side="left", padx=5)
            vtxt = tk.StringVar(value=step.get("text", ""))
            et = tk.Entry(row, textvariable=vtxt, width=20, bg=self.PANEL, fg=self.TEXT, relief="flat"); et.pack(side="left")
            et.bind("<KeyRelease>", lambda ev, st=step, vr=vtxt: st.update({"text": vr.get()}) or self._save_auto())
            
        elif cmd == "find_image":
            stk = tk.Frame(row, bg=self.CARD)
            stk.pack(side="left", padx=5)

            l1 = tk.Frame(stk, bg=self.CARD)
            l1.pack(fill="x", pady=1)
            tk.Label(l1, text="🖼 Find Image", bg=self.CARD, fg="#b072ff", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0,5))
            vimg = tk.StringVar(value=step.get("image", ""))
            eimg = tk.Entry(l1, textvariable=vimg, width=15, bg=self.PANEL, fg=self.TEXT, relief="flat"); eimg.pack(side="left")
            eimg.bind("<KeyRelease>", lambda ev, st=step, vr=vimg: st.update({"image": vr.get()}) or self._save_auto())
            tk.Button(l1, text="📂 File", bg=self.CARD, fg=self.SUB, relief="flat", command=lambda st=step, vr=vimg: (p:=filedialog.askopenfilename()) and (vr.set(p) or st.update({"image": p}) or self._save_auto())).pack(side="left", padx=2)
            tk.Button(l1, text="✂️ Snip", bg=self.CARD, fg=self.SUB, relief="flat", command=lambda st=step, vr=vimg: self._snip_image(st, vr)).pack(side="left")

            l2 = tk.Frame(stk, bg=self.CARD)
            l2.pack(fill="x", pady=1)
            tk.Label(l2, text="Action:", bg=self.CARD, fg=self.SUB).pack(side="left")
            vact = tk.StringVar(value=step.get("action", "click"))
            cb2 = ttk.Combobox(l2, textvariable=vact, values=["click", "move", "double_click", "right_click", "none"], width=10, state="readonly")
            cb2.pack(side="left", padx=2)
            cb2.bind("<<ComboboxSelected>>", lambda ev, st=step, vr=vact: st.update({"action": vr.get()}) or self._save_auto())
            
            tk.Label(l2, text="Match%:", bg=self.CARD, fg=self.SUB).pack(side="left", padx=(5,0))
            vconf = tk.StringVar(value=str(step.get("confidence", 80)))
            econf = tk.Entry(l2, textvariable=vconf, width=4, bg=self.PANEL, fg=self.TEXT, relief="flat"); econf.pack(side="left")
            econf.bind("<KeyRelease>", lambda ev, st=step, vr=vconf: st.update({"confidence": int(vr.get()) if vr.get().isdigit() else 80}) or self._save_auto())

            tk.Label(l2, text="Timeout(s):", bg=self.CARD, fg=self.SUB).pack(side="left", padx=(5,0))
            vtime = tk.StringVar(value=str(step.get("timeout", 0)))
            etime = tk.Entry(l2, textvariable=vtime, width=4, bg=self.PANEL, fg=self.TEXT, relief="flat"); etime.pack(side="left")
            etime.bind("<KeyRelease>", lambda ev, st=step, vr=vtime: st.update({"timeout": int(vr.get()) if vr.get().isdigit() else 0}) or self._save_auto())

            l3 = tk.Frame(stk, bg=self.CARD)
            l3.pack(fill="x", pady=1)
            tk.Label(l3, text="Timeout Act:", bg=self.CARD, fg=self.SUB).pack(side="left")
            vtout = tk.StringVar(value=step.get("timeout_action", "stop"))
            cbt = ttk.Combobox(l3, textvariable=vtout, values=["stop", "continue"], width=8, state="readonly")
            cbt.pack(side="left", padx=2)
            cbt.bind("<<ComboboxSelected>>", lambda ev, st=step, vr=vtout: st.update({"timeout_action": vr.get()}) or self._save_auto())
            
            vcor = tk.BooleanVar(value=step.get("move_corner", False))
            ck = tk.Checkbutton(l3, text="Move Corner", bg=self.CARD, fg=self.SUB, selectcolor=self.PANEL, activebackground=self.CARD, activeforeground=self.SUB, variable=vcor, command=lambda st=step, vr=vcor: st.update({"move_corner": vr.get()}) or self._save_auto())
            ck.pack(side="left", padx=5)
            
            vtween = tk.BooleanVar(value=step.get("tween", False))
            ckt = tk.Checkbutton(l3, text="Tween", bg=self.CARD, fg=self.SUB, selectcolor=self.PANEL, activebackground=self.CARD, activeforeground=self.SUB, variable=vtween, command=lambda st=step, vr=vtween: st.update({"tween": vr.get()}) or self._save_auto())
            ckt.pack(side="left", padx=5)

        elif cmd == "if_image":
            tk.Label(row, text="🔀 If Image", bg=self.CARD, fg="#47a0ff", font=("Segoe UI", 9, "bold")).pack(side="left", padx=5)
            vimg = tk.StringVar(value=step.get("image", ""))
            eimg = tk.Entry(row, textvariable=vimg, width=15, bg=self.PANEL, fg=self.TEXT, relief="flat"); eimg.pack(side="left")
            eimg.bind("<KeyRelease>", lambda ev, st=step, vr=vimg: st.update({"image": vr.get()}) or self._save_auto())
            tk.Button(row, text="📂", bg=self.CARD, fg=self.SUB, relief="flat", command=lambda st=step, vr=vimg: (p:=filedialog.askopenfilename()) and (vr.set(p) or st.update({"image": p}) or self._save_auto())).pack(side="left", padx=2)
            tk.Button(row, text="✂️ Snip", bg=self.CARD, fg=self.SUB, relief="flat", command=lambda st=step, vr=vimg: self._snip_image(st, vr)).pack(side="left", padx=2)
            
            tk.Label(row, text="Match%:", bg=self.CARD, fg=self.SUB).pack(side="left", padx=(5,0))
            vconf = tk.StringVar(value=str(step.get("confidence", 80)))
            econf = tk.Entry(row, textvariable=vconf, width=4, bg=self.PANEL, fg=self.TEXT, relief="flat"); econf.pack(side="left")
            econf.bind("<KeyRelease>", lambda ev, st=step, vr=vconf: st.update({"confidence": int(vr.get()) if vr.get().isdigit() else 80}) or self._save_auto())
            
        elif cmd == "else":
            tk.Label(row, text="➖ Else", bg=self.CARD, fg="#47a0ff", font=("Segoe UI", 9, "bold")).pack(side="left", padx=5)
            
        elif cmd == "end_if":
            tk.Label(row, text="🛑 End If", bg=self.CARD, fg="#47a0ff", font=("Segoe UI", 9, "bold")).pack(side="left", padx=5)

        ctrls = tk.Frame(row, bg=self.CARD)
        ctrls.pack(side="right", padx=5)
        
        tk.Label(ctrls, text="Delay(ms):", bg=self.CARD, fg=self.SUB).pack(side="left")
        vda = tk.StringVar(value=str(step.get("delay_after", 0)))
        eda = tk.Entry(ctrls, textvariable=vda, width=5, bg=self.PANEL, fg=self.TEXT, relief="flat"); eda.pack(side="left", padx=2)
        eda.bind("<KeyRelease>", lambda ev, st=step, vr=vda: st.update({"delay_after": int(vr.get()) if vr.get().isdigit() else 0}) or self._save_auto())

        tk.Button(ctrls, text="↑", bg=self.PANEL, fg=self.SUB, relief="flat", width=2, command=lambda: self._move_step(idx, -1)).pack(side="left", padx=1)
        tk.Button(ctrls, text="↓", bg=self.PANEL, fg=self.SUB, relief="flat", width=2, command=lambda: self._move_step(idx, 1)).pack(side="left", padx=1)
        tk.Button(ctrls, text="✕", bg=self.PANEL, fg="#ff002b", relief="flat", width=2, command=lambda: self._del_step(idx)).pack(side="left", padx=1)
