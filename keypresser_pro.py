"""
KeyPresser Pro v5
Toggle dark/light — Demo 5 min — Licence Stripe/Supabase
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading
import time
import json
import os
import hashlib
import uuid
import webbrowser
import requests
from pynput.keyboard import Key, Controller
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE     = "https://bright-swan-a18b6a.netlify.app/.netlify/functions"
VERIFY_URL   = f"{API_BASE}/verify-license"
CHECKOUT_URL = "https://bright-swan-a18b6a.netlify.app"
# Meme fichier que v4 pour recuperer la licence existante
LICENSE_FILE = os.path.join(os.path.expanduser("~"), ".keypresser_v4.json")
THEME_FILE   = os.path.join(os.path.expanduser("~"), ".keypresser_theme.txt")
DEMO_SECONDS = 5 * 60

SPECIAL_KEYS = {
    "Verr. Maj (Caps Lock)": Key.caps_lock,
    "Verr. Num (Num Lock)":  Key.num_lock,
    "F15 (Keep-alive)":      Key.f15,
    "Espace":                Key.space,
    "Entree":                Key.enter,
    "Echap":                 Key.esc,
    "Tab":                   Key.tab,
    "Maj (Shift)":           Key.shift,
    "Ctrl":                  Key.ctrl,
    "Alt":                   Key.alt,
    "F5":                    Key.f5,
    "F6":                    Key.f6,
    "Fleche haut":           Key.up,
    "Fleche bas":            Key.down,
    "Fleche gauche":         Key.left,
    "Fleche droite":         Key.right,
}
DAYS_FR = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
keyboard_ctrl = Controller()

# ── Palette de couleurs selon le theme ────────────────────────────────────────
COLORS = {
    "dark": {
        "accent":        "#7c6af7",
        "accent_hover":  "#5b4fd4",
        "success":       "#16a34a",
        "success_hover": "#15803d",
        "warning":       "#d97706",
        "warning_hover": "#b45309",
        "danger":        "#dc2626",
        "danger_hover":  "#b91c1c",
        "banner_demo":   "#1e1400",
        "banner_lic":    "#0a1e14",
        "banner_text_demo": "#f0c060",
        "banner_text_lic":  "#4caf84",
        "log_text":      "#4ade80",
        "btn_border":    "#3a3a6a",
        "del_hover":     "#3f1515",
        # Hover léger pour boutons transparents (texte reste visible)
        "ghost_hover":   "#2a2a4a",
        "ghost_del_hover": "#2a1010",
        "ghost_text":    "#c0b8ff",  # texte clair sur fond sombre
        "ghost_del_text": "#ff8080",
    },
    "light": {
        "accent":        "#6d5ce8",
        "accent_hover":  "#5546c7",
        "success":       "#15803d",
        "success_hover": "#166534",
        "warning":       "#b45309",
        "warning_hover": "#92400e",
        "danger":        "#b91c1c",
        "danger_hover":  "#991b1b",
        "banner_demo":   "#fef3c7",
        "banner_lic":    "#dcfce7",
        "banner_text_demo": "#92400e",
        "banner_text_lic":  "#166534",
        "log_text":      "#15803d",
        "btn_border":    "#c7c7d4",
        "del_hover":     "#fee2e2",
        # Hover léger pour boutons transparents (texte reste visible)
        "ghost_hover":   "#ebe8ff",
        "ghost_del_hover": "#fde8e8",
        "ghost_text":    "#5546c7",  # texte violet foncé sur fond clair
        "ghost_del_text": "#b91c1c",
    }
}

# ── Theme ─────────────────────────────────────────────────────────────────────
def load_theme():
    try:
        with open(THEME_FILE) as f:
            t = f.read().strip()
            return t if t in ("dark","light") else "dark"
    except:
        return "dark"

def save_theme(t):
    with open(THEME_FILE, "w") as f: f.write(t)

# ── Machine ID ────────────────────────────────────────────────────────────────
def get_machine_id():
    mid_file = os.path.join(os.path.expanduser("~"), ".kp_mid")
    if os.path.exists(mid_file):
        with open(mid_file) as f: return f.read().strip()
    mid = str(uuid.uuid4())
    with open(mid_file, "w") as f: f.write(mid)
    return mid

MACHINE_ID = get_machine_id()

# ── Licence ───────────────────────────────────────────────────────────────────
def verify_license_online(key):
    try:
        r = requests.post(VERIFY_URL,
            json={"license_key": key, "machine_id": MACHINE_ID}, timeout=8)
        data = r.json()
        if data.get("valid"): return True, data.get("email","")
        return False, data.get("error","Licence invalide.")
    except:
        return False, "Connexion impossible."

def save_license(key, email):
    # Compatible avec le hash v4
    h = hashlib.sha256((key + MACHINE_ID + "kp_v4").encode()).hexdigest()
    with open(LICENSE_FILE, "w") as f:
        json.dump({"key": key, "email": email, "hash": h}, f)

def load_license():
    if not os.path.exists(LICENSE_FILE): return None, None
    try:
        with open(LICENSE_FILE) as f: data = json.load(f)
        k, e = data.get("key",""), data.get("email","")
        # Essaie v4 d'abord, puis v5
        for salt in ["kp_v4", "kp_v5"]:
            if hashlib.sha256((k+MACHINE_ID+salt).encode()).hexdigest() == data.get("hash",""):
                return k, e
    except: pass
    return None, None

# ─────────────────────────────────────────────────────────────────────────────
# Etat global
# ─────────────────────────────────────────────────────────────────────────────
class AppState:
    theme         = load_theme()
    licensed      = False
    demo_mode     = False
    demo_end      = None
    license_email = ""
    sequence_items = []
    profiles      = {}
    mode          = "Touche simple"
    key_choice    = "Verr. Maj (Caps Lock)"
    interval      = 60
    hours         = "10"; mins = "0"
    infinite      = False
    days          = [True]*7
    start_h="08"; start_m="00"; end_h="18"; end_m="00"
    planning      = False
    profile_name  = "Mon profil"

state = AppState()

def C(key):
    """Raccourci pour obtenir la couleur selon le theme actuel."""
    return COLORS[state.theme][key]

# ─────────────────────────────────────────────────────────────────────────────
# Fenetre licence
# ─────────────────────────────────────────────────────────────────────────────
class LicenseWindow(ctk.CTkToplevel):
    def __init__(self, parent, on_success, on_quit):
        super().__init__(parent)
        self.on_success = on_success
        self.on_quit    = on_quit
        self.title("KeyPresser Pro — Activation")
        self.geometry("520x340")
        self.resizable(False, False)
        self.grab_set()
        self.focus_force()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._keep_grab()
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, corner_radius=0, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="KeyPresser",
                     font=ctk.CTkFont("Courier New", 22, "bold")).pack(side="left", padx=20, pady=18)
        ctk.CTkLabel(header, text=" Pro",
                     font=ctk.CTkFont("Courier New", 22, "bold"),
                     text_color=C("accent")).pack(side="left", pady=18)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=32, pady=20)

        ctk.CTkLabel(body,
                     text="Votre periode d'essai est terminee.\nActivez votre licence pour continuer.",
                     font=ctk.CTkFont("Courier New", 12), justify="center").pack(pady=(0,16))

        self.entry = ctk.CTkEntry(body, placeholder_text="KP-XXXX-XXXX-XXXX-XXXX",
                                  font=ctk.CTkFont("Courier New", 13), height=44)
        self.entry.pack(fill="x", pady=(0,8))
        self.entry.bind("<Return>", lambda e: self._activate())

        self.status = ctk.CTkLabel(body, text="", font=ctk.CTkFont("Courier New", 10))
        self.status.pack(pady=(0,10))

        btn_f = ctk.CTkFrame(body, fg_color="transparent")
        btn_f.pack(fill="x")
        btn_f.grid_columnconfigure((0,1), weight=1)

        ctk.CTkButton(btn_f, text="Activer la licence", height=42, corner_radius=8,
                      font=ctk.CTkFont("Courier New", 12, "bold"),
                      fg_color=C("accent"), hover_color=C("accent_hover"),
                      command=self._activate).grid(row=0, column=0, padx=(0,6), sticky="ew")

        ctk.CTkButton(btn_f, text="Acheter — 4,99EUR", height=42, corner_radius=8,
                      font=ctk.CTkFont("Courier New", 12, "bold"),
                      fg_color="transparent", hover_color=C("accent"),
                      border_width=2, border_color=C("accent"), text_color=C("accent"),
                      command=self._buy).grid(row=0, column=1, padx=(6,0), sticky="ew")

        ctk.CTkLabel(body, text="Paiement securise · Cle par mail instantanement",
                     font=ctk.CTkFont("Courier New", 9)).pack(pady=(10,0))

    def _keep_grab(self):
        try:
            if self.winfo_exists():
                self.grab_set()
                self.after(1000, self._keep_grab)
        except: pass

    def _buy(self):
        webbrowser.open(CHECKOUT_URL)
        self.after(600, lambda: [self.grab_set(), self.focus_force(), self.lift()])

    def _activate(self):
        key = self.entry.get().strip()
        if not key:
            self.status.configure(text="Veuillez entrer une cle.", text_color="#e05c6a"); return
        self.status.configure(text="Verification...", text_color=C("accent"))
        self.update()
        ok, msg = verify_license_online(key)
        if ok:
            save_license(key, msg)
            self.status.configure(text="Licence activee !", text_color=C("success"))
            self.after(600, lambda: [self.destroy(), self.on_success(key, msg)])
        else:
            self.status.configure(text=f"Erreur : {msg}", text_color="#e05c6a")

    def _on_close(self):
        self.grab_release()
        if messagebox.askyesno("Quitter ?", "Voulez-vous quitter KeyPresser Pro ?", parent=self):
            self.destroy(); self.on_quit()
        else:
            self.grab_set(); self.focus_force(); self.lift()

# ─────────────────────────────────────────────────────────────────────────────
# Application principale
# ─────────────────────────────────────────────────────────────────────────────
class KeyPresserPro(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode(state.theme)
        ctk.set_default_color_theme("blue")
        self.title("KeyPresser Pro")
        self.geometry("700x730")
        self.minsize(660, 660)
        self.resizable(True, True)

        self.running      = False
        self.paused       = False
        self.thread       = None
        self.start_time   = None
        self.presses_done = 0
        self.next_press_at = None

        self._build_ui()
        self._restore_state()

        key, email = load_license()
        if key:
            self._set_banner_checking()
            threading.Thread(target=self._verify_on_start, args=(key, email), daemon=True).start()
        else:
            self._start_demo()

    # ── State save/restore ────────────────────────────────────────────────────

    def _restore_state(self):
        self.mode_var.set(state.mode)
        self.key_var.set(state.key_choice)
        self.interval_var.set(state.interval)
        self.interval_lbl.configure(text=f"{state.interval} s")
        self.hours_var.set(state.hours); self.mins_var.set(state.mins)
        self.infinite_var.set(state.infinite)
        for i,v in enumerate(state.days): self.day_vars[i].set(v)
        self.start_hour.set(state.start_h); self.start_min.set(state.start_m)
        self.end_hour.set(state.end_h);    self.end_min.set(state.end_m)
        self.planning_enabled.set(state.planning)
        self.profile_name_var.set(state.profile_name)
        self._seq_refresh()
        self._profile_refresh()

    def _save_state(self):
        state.mode      = self.mode_var.get()
        state.key_choice = self.key_var.get()
        state.interval  = self.interval_var.get()
        state.hours     = self.hours_var.get(); state.mins = self.mins_var.get()
        state.infinite  = self.infinite_var.get()
        state.days      = [v.get() for v in self.day_vars]
        state.start_h   = self.start_hour.get(); state.start_m = self.start_min.get()
        state.end_h     = self.end_hour.get();   state.end_m   = self.end_min.get()
        state.planning  = self.planning_enabled.get()
        state.profile_name = self.profile_name_var.get()

    # ── Licence ───────────────────────────────────────────────────────────────

    def _set_banner_checking(self):
        self.banner_label.configure(text="  Verification licence...", text_color="gray")
        self.banner_frame.configure(fg_color="transparent")

    def _verify_on_start(self, key, email):
        ok, msg = verify_license_online(key)
        if ok:
            state.licensed = True; state.license_email = email
            self.after(0, lambda: self._set_banner_licensed(email))
        else:
            try: os.remove(LICENSE_FILE)
            except: pass
            state.licensed = False
            self.after(0, self._on_license_revoked)

    def _on_license_revoked(self):
        messagebox.showwarning("Licence suspendue",
            "Votre licence a ete suspendue.\nVeuillez contacter le support.")
        self._show_license_window()

    def _show_license_window(self):
        LicenseWindow(self, self._on_license_ok, self.destroy)

    def _on_license_ok(self, key, email):
        state.licensed = True; state.demo_mode = False; state.license_email = email
        self._set_banner_licensed(email)

    def _set_banner_licensed(self, email=""):
        txt = "  LICENCE ACTIVE"
        if email: txt += f"  —  {email}"
        self.banner_label.configure(text=txt, text_color=C("banner_text_lic"))
        self.banner_frame.configure(fg_color=C("banner_lic"))
        self.btn_buy_banner.pack_forget()
        self.btn_activate_banner.pack_forget()
        self.btn_help_banner.pack(side="right", padx=8, pady=5)

    # ── Demo ─────────────────────────────────────────────────────────────────

    def _start_demo(self):
        state.demo_mode = True; state.licensed = False
        state.demo_end = time.time() + DEMO_SECONDS
        self._update_demo_banner()
        self._log("Mode demo — 5 minutes pour essayer gratuitement.")

    def _update_demo_banner(self):
        if not state.demo_mode: return
        remaining = max(0, state.demo_end - time.time())
        m, s = divmod(int(remaining), 60)
        self.banner_label.configure(
            text=f"  DEMO  —  {m:02d}:{s:02d} restantes  —  Achetez pour tout debloquer",
            text_color=C("banner_text_demo"))
        self.banner_frame.configure(fg_color=C("banner_demo"))
        if remaining <= 0: self._demo_expired()
        else: self.after(1000, self._update_demo_banner)

    def _demo_expired(self):
        state.demo_mode = False
        if self.running: self.stop()
        self.after(300, self._show_license_window)

    # ── Toggle theme ──────────────────────────────────────────────────────────

    def _toggle_theme(self):
        if self.running:
            messagebox.showinfo("Info","Arretez la session avant de changer le theme."); return
        self._save_state()
        state.theme = "light" if state.theme == "dark" else "dark"
        save_theme(state.theme)
        self.destroy()
        KeyPresserPro().mainloop()

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        is_dark = state.theme == "dark"

        # Banner
        self.banner_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0, height=32)
        self.banner_frame.pack(fill="x")
        self.banner_frame.pack_propagate(False)
        self.banner_label = ctk.CTkLabel(self.banner_frame, text="  Chargement...",
            font=ctk.CTkFont("Courier New", 10, "bold"), anchor="w")
        self.banner_label.pack(side="left", fill="x", expand=True, padx=8)

        self.btn_buy_banner = ctk.CTkButton(self.banner_frame, text="Acheter 4,99EUR",
            width=110, height=22, font=ctk.CTkFont("Courier New", 9, "bold"),
            fg_color=C("accent"), hover_color=C("accent_hover"), text_color="#ffffff",
            corner_radius=4, command=lambda: webbrowser.open(CHECKOUT_URL))
        self.btn_buy_banner.pack(side="right", padx=8, pady=5)

        self.btn_activate_banner = ctk.CTkButton(self.banner_frame, text="Activer",
            width=70, height=22, font=ctk.CTkFont("Courier New", 9),
            fg_color="transparent", hover_color=C("ghost_hover"),
            border_width=1, border_color=C("accent"), text_color=C("ghost_text"),
            corner_radius=4, command=self._show_license_window)
        self.btn_activate_banner.pack(side="right", padx=(0,4), pady=5)

        self.btn_help_banner = ctk.CTkButton(self.banner_frame, text="Aide",
            width=60, height=22, font=ctk.CTkFont("Courier New", 9),
            fg_color="transparent", hover_color=C("ghost_hover"),
            border_width=1, border_color=C("btn_border"),
            text_color=C("ghost_text"), corner_radius=4,
            command=lambda: webbrowser.open(CHECKOUT_URL))

        # Header
        header = ctk.CTkFrame(self, corner_radius=0, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        logo_f = ctk.CTkFrame(header, fg_color="transparent")
        logo_f.pack(side="left", padx=20, pady=12)
        ctk.CTkLabel(logo_f, text="KeyPresser",
                     font=ctk.CTkFont("Courier New", 20, "bold")).pack(side="left")
        ctk.CTkLabel(logo_f, text=" Pro",
                     font=ctk.CTkFont("Courier New", 20, "bold"),
                     text_color=C("accent")).pack(side="left")

        theme_icon = "☀" if is_dark else "🌙"
        theme_lbl  = " Light" if is_dark else " Dark"
        ctk.CTkButton(header, text=theme_icon + theme_lbl, width=80, height=30,
                      font=ctk.CTkFont("Courier New", 11),
                      fg_color="transparent", hover_color=C("ghost_hover"),
                      border_width=1, border_color=C("btn_border"),
                      text_color=C("ghost_text"), corner_radius=6,
                      command=self._toggle_theme).pack(side="right", padx=12, pady=16)

        ctk.CTkFrame(self, height=1, corner_radius=0).pack(fill="x")

        # Tabs
        self.tabs = ctk.CTkTabview(self, height=350,
                                    segmented_button_selected_color=C("accent"),
                                    segmented_button_selected_hover_color=C("accent_hover"))
        self.tabs.pack(fill="x", padx=16, pady=(10,0))
        for t in ["  Config  ","  Sequence  ","  Planning  ","  Profils  "]:
            self.tabs.add(t)

        self._build_config_tab()
        self._build_sequence_tab()
        self._build_planning_tab()
        self._build_profiles_tab()
        self._build_status_bar()
        self._build_buttons()
        self._build_log()

    # ── Tab Config ────────────────────────────────────────────────────────────

    def _build_config_tab(self):
        tab = self.tabs.tab("  Config  ")
        tab.grid_columnconfigure(1, weight=1)
        P = {"padx": 14, "pady": 8}

        def lbl(row, text):
            ctk.CTkLabel(tab, text=text, font=ctk.CTkFont("Courier New", 11),
                         anchor="w").grid(row=row, column=0, sticky="w", **P)

        lbl(0, "Mode")
        self.mode_var = ctk.StringVar(value="Touche simple")
        ctk.CTkSegmentedButton(tab, values=["Touche simple","Sequence"],
                               variable=self.mode_var,
                               font=ctk.CTkFont("Courier New", 10),
                               selected_color=C("accent"),
                               selected_hover_color=C("accent_hover")
                               ).grid(row=0, column=1, sticky="ew", **P)

        lbl(1, "Touche")
        self.key_var = ctk.StringVar(value="Verr. Maj (Caps Lock)")
        ctk.CTkOptionMenu(tab, variable=self.key_var,
                          values=list(SPECIAL_KEYS.keys()),
                          font=ctk.CTkFont("Courier New", 10),
                          button_color=C("accent"), button_hover_color=C("accent_hover"),
                          width=260).grid(row=1, column=1, sticky="w", **P)

        lbl(2, "Intervalle")
        iv = ctk.CTkFrame(tab, fg_color="transparent")
        iv.grid(row=2, column=1, sticky="ew", **P)
        self.interval_var = ctk.IntVar(value=60)
        self.interval_lbl = ctk.CTkLabel(iv, text="60 s", width=52,
                                          font=ctk.CTkFont("Courier New", 12, "bold"),
                                          text_color=C("accent"))
        self.interval_lbl.pack(side="right")
        ctk.CTkSlider(iv, from_=5, to=600, variable=self.interval_var,
                      button_color=C("accent"), button_hover_color=C("accent_hover"),
                      progress_color=C("accent"),
                      command=lambda v: self.interval_lbl.configure(text=f"{int(v)} s")
                      ).pack(side="left", fill="x", expand=True, padx=(0,8))

        lbl(3, "Duree")
        dur = ctk.CTkFrame(tab, fg_color="transparent")
        dur.grid(row=3, column=1, sticky="w", **P)
        self.hours_var = ctk.StringVar(value="10")
        self.mins_var  = ctk.StringVar(value="0")
        for ltext, var in [("H", self.hours_var), ("min", self.mins_var)]:
            ctk.CTkLabel(dur, text=ltext, font=ctk.CTkFont("Courier New", 10)).pack(side="left")
            ctk.CTkEntry(dur, textvariable=var, width=52,
                         font=ctk.CTkFont("Courier New", 11)).pack(side="left", padx=(3,10))
        self.infinite_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(dur, text="Infini", variable=self.infinite_var,
                        font=ctk.CTkFont("Courier New", 10),
                        fg_color=C("accent"), hover_color=C("accent_hover"),
                        checkmark_color="#ffffff").pack(side="left")

    # ── Tab Sequence ──────────────────────────────────────────────────────────

    def _build_sequence_tab(self):
        tab = self.tabs.tab("  Sequence  ")
        ctk.CTkLabel(tab, text="Sequencez plusieurs touches. Licence requise.",
                     font=ctk.CTkFont("Courier New", 10)).pack(pady=(8,6))

        add = ctk.CTkFrame(tab, corner_radius=8)
        add.pack(fill="x", padx=12, pady=4)
        inner = ctk.CTkFrame(add, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=10)

        self.seq_key_var = ctk.StringVar(value="Verr. Maj (Caps Lock)")
        ctk.CTkOptionMenu(inner, variable=self.seq_key_var,
                          values=list(SPECIAL_KEYS.keys()),
                          font=ctk.CTkFont("Courier New", 10),
                          button_color=C("accent"), button_hover_color=C("accent_hover"),
                          width=200).pack(side="left", padx=(0,8))
        ctk.CTkLabel(inner, text="ms", font=ctk.CTkFont("Courier New", 9)).pack(side="left")
        self.seq_delay_var = ctk.StringVar(value="500")
        ctk.CTkEntry(inner, textvariable=self.seq_delay_var, width=64,
                     font=ctk.CTkFont("Courier New", 10)).pack(side="left", padx=(4,8))
        ctk.CTkButton(inner, text="+ Ajouter", width=90, height=30,
                      font=ctk.CTkFont("Courier New", 10, "bold"),
                      fg_color=C("accent"), hover_color=C("accent_hover"),
                      text_color="#ffffff", corner_radius=6,
                      command=self._seq_add).pack(side="left")

        self.seq_frame = ctk.CTkScrollableFrame(tab, height=170)
        self.seq_frame.pack(fill="x", padx=12, pady=4)

        ctk.CTkButton(tab, text="Vider la liste", width=100, height=28,
                      font=ctk.CTkFont("Courier New", 9),
                      fg_color="transparent", hover_color=C("ghost_del_hover"),
                      border_width=1, border_color=C("danger"),
                      text_color=C("ghost_del_text"), corner_radius=6,
                      command=self._seq_clear).pack(anchor="w", padx=12, pady=4)

    def _seq_add(self):
        if not state.licensed:
            messagebox.showinfo("Licence requise", "Les sequences necessitent une licence."); return
        key = self.seq_key_var.get()
        try: delay = int(self.seq_delay_var.get())
        except: delay = 500
        state.sequence_items.append((key, delay))
        self._seq_refresh()

    def _seq_clear(self):
        state.sequence_items.clear(); self._seq_refresh()

    def _seq_refresh(self):
        for w in self.seq_frame.winfo_children(): w.destroy()
        for i, (key, delay) in enumerate(state.sequence_items):
            row = ctk.CTkFrame(self.seq_frame, corner_radius=6, height=36)
            row.pack(fill="x", pady=2); row.pack_propagate(False)
            ctk.CTkLabel(row, text=f"{i+1:02d}", width=28,
                         font=ctk.CTkFont("Courier New", 10)).pack(side="left", padx=6)
            ctk.CTkLabel(row, text=key,
                         font=ctk.CTkFont("Courier New", 10)).pack(side="left", padx=4)
            ctk.CTkLabel(row, text=f"{delay}ms",
                         font=ctk.CTkFont("Courier New", 9),
                         text_color=C("accent")).pack(side="left", padx=8)
            ctk.CTkButton(row, text="✕", width=26, height=22,
                          font=ctk.CTkFont("Courier New", 9),
                          fg_color="transparent", hover_color=C("ghost_del_hover"),
                          text_color=C("ghost_del_text"), corner_radius=4,
                          command=lambda i=i: self._seq_remove(i)).pack(side="right", padx=6)

    def _seq_remove(self, i):
        state.sequence_items.pop(i); self._seq_refresh()

    # ── Tab Planning ──────────────────────────────────────────────────────────

    def _build_planning_tab(self):
        tab = self.tabs.tab("  Planning  ")

        ctk.CTkLabel(tab, text="Jours actifs",
                     font=ctk.CTkFont("Courier New", 11)).pack(pady=(14,8))
        days_f = ctk.CTkFrame(tab, corner_radius=8)
        days_f.pack(padx=12, pady=(0,12))
        inner_d = ctk.CTkFrame(days_f, fg_color="transparent")
        inner_d.pack(padx=16, pady=10)
        self.day_vars = []
        for d in DAYS_FR:
            v = ctk.BooleanVar(value=True)
            self.day_vars.append(v)
            ctk.CTkCheckBox(inner_d, text=d, variable=v, width=56,
                            font=ctk.CTkFont("Courier New", 10),
                            fg_color=C("accent"), hover_color=C("accent_hover"),
                            checkmark_color="#ffffff").pack(side="left", padx=3)

        ctk.CTkLabel(tab, text="Plage horaire",
                     font=ctk.CTkFont("Courier New", 11)).pack(pady=(4,8))
        time_f = ctk.CTkFrame(tab, corner_radius=8)
        time_f.pack(padx=12)
        tf = ctk.CTkFrame(time_f, fg_color="transparent")
        tf.pack(padx=20, pady=14)

        self.start_hour = ctk.StringVar(value="08"); self.start_min = ctk.StringVar(value="00")
        self.end_hour   = ctk.StringVar(value="18"); self.end_min   = ctk.StringVar(value="00")

        def te(hv, mv):
            f = ctk.CTkFrame(tf, fg_color="transparent")
            ctk.CTkEntry(f, textvariable=hv, width=48, justify="center",
                         font=ctk.CTkFont("Courier New", 13)).pack(side="left")
            ctk.CTkLabel(f, text=":", font=ctk.CTkFont("Courier New", 16, "bold")).pack(side="left", padx=2)
            ctk.CTkEntry(f, textvariable=mv, width=48, justify="center",
                         font=ctk.CTkFont("Courier New", 13)).pack(side="left")
            return f

        ctk.CTkLabel(tf, text="De", font=ctk.CTkFont("Courier New", 10)).pack(side="left", padx=(0,8))
        te(self.start_hour, self.start_min).pack(side="left")
        ctk.CTkLabel(tf, text="  à", font=ctk.CTkFont("Courier New", 10)).pack(side="left", padx=10)
        te(self.end_hour, self.end_min).pack(side="left")

        self.planning_enabled = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(tab, text="Activer le planning (Licence requise)",
                        variable=self.planning_enabled,
                        font=ctk.CTkFont("Courier New", 10),
                        fg_color=C("accent"), hover_color=C("accent_hover"),
                        checkmark_color="#ffffff").pack(pady=14)

    def _in_schedule(self):
        if not self.planning_enabled.get() or not state.licensed: return True
        now = datetime.now()
        if not self.day_vars[now.weekday()].get(): return False
        try:
            sh,sm = int(self.start_hour.get()),int(self.start_min.get())
            eh,em = int(self.end_hour.get()),int(self.end_min.get())
        except: return True
        cur = now.hour*60+now.minute
        return (sh*60+sm) <= cur < (eh*60+em)

    # ── Tab Profils ───────────────────────────────────────────────────────────

    def _build_profiles_tab(self):
        tab = self.tabs.tab("  Profils  ")
        ctk.CTkLabel(tab, text="Sauvegardez vos configurations. Licence requise.",
                     font=ctk.CTkFont("Courier New", 10)).pack(pady=(8,6))

        nf = ctk.CTkFrame(tab, corner_radius=8)
        nf.pack(fill="x", padx=12, pady=4)
        inner_nf = ctk.CTkFrame(nf, fg_color="transparent")
        inner_nf.pack(fill="x", padx=12, pady=10)
        ctk.CTkLabel(inner_nf, text="Nom :",
                     font=ctk.CTkFont("Courier New", 10)).pack(side="left")
        self.profile_name_var = ctk.StringVar(value="Mon profil")
        ctk.CTkEntry(inner_nf, textvariable=self.profile_name_var, width=180,
                     font=ctk.CTkFont("Courier New", 10)).pack(side="left", padx=8)
        ctk.CTkButton(inner_nf, text="Sauver", width=80, height=30,
                      font=ctk.CTkFont("Courier New", 10, "bold"),
                      fg_color=C("accent"), hover_color=C("accent_hover"),
                      text_color="#ffffff", corner_radius=6,
                      command=self._profile_save).pack(side="left")

        self.profile_list = ctk.CTkScrollableFrame(tab, height=140)
        self.profile_list.pack(fill="x", padx=12, pady=4)

        io = ctk.CTkFrame(tab, fg_color="transparent")
        io.pack(fill="x", padx=12, pady=4)
        for txt, cmd in [("Exporter JSON", self._profile_export), ("Importer JSON", self._profile_import)]:
            ctk.CTkButton(io, text=txt, width=120, height=28,
                          font=ctk.CTkFont("Courier New", 9),
                          fg_color="transparent", hover_color=C("ghost_hover"),
                          border_width=1, border_color=C("btn_border"),
                          text_color=C("ghost_text"), corner_radius=6,
                          command=cmd).pack(side="left", padx=(0,6))

    def _get_config(self):
        return {
            "mode": self.mode_var.get(), "key": self.key_var.get(),
            "interval": self.interval_var.get(),
            "hours": self.hours_var.get(), "mins": self.mins_var.get(),
            "infinite": self.infinite_var.get(),
            "sequence": state.sequence_items,
            "days": [v.get() for v in self.day_vars],
            "start_h": self.start_hour.get(), "start_m": self.start_min.get(),
            "end_h": self.end_hour.get(), "end_m": self.end_min.get(),
            "planning": self.planning_enabled.get(),
        }

    def _apply_config(self, cfg):
        self.mode_var.set(cfg.get("mode","Touche simple"))
        self.key_var.set(cfg.get("key","Verr. Maj (Caps Lock)"))
        self.interval_var.set(cfg.get("interval",60))
        self.interval_lbl.configure(text=f"{cfg.get('interval',60)} s")
        self.hours_var.set(cfg.get("hours","10")); self.mins_var.set(cfg.get("mins","0"))
        self.infinite_var.set(cfg.get("infinite",False))
        state.sequence_items = cfg.get("sequence",[]); self._seq_refresh()
        for i,v in enumerate(cfg.get("days",[True]*7)): self.day_vars[i].set(v)
        self.start_hour.set(cfg.get("start_h","08")); self.start_min.set(cfg.get("start_m","00"))
        self.end_hour.set(cfg.get("end_h","18")); self.end_min.set(cfg.get("end_m","00"))
        self.planning_enabled.set(cfg.get("planning",False))

    def _profile_save(self):
        if not state.licensed:
            messagebox.showinfo("Licence requise","Necessite une licence."); return
        name = self.profile_name_var.get().strip()
        if not name: return
        state.profiles[name] = self._get_config()
        self._profile_refresh(); self._log(f"Profil '{name}' sauvegarde.")

    def _profile_refresh(self):
        for w in self.profile_list.winfo_children(): w.destroy()
        for name in state.profiles:
            row = ctk.CTkFrame(self.profile_list, corner_radius=6, height=34)
            row.pack(fill="x", pady=2); row.pack_propagate(False)
            ctk.CTkLabel(row, text=name,
                         font=ctk.CTkFont("Courier New",10)).pack(side="left",padx=10)
            ctk.CTkButton(row,text="Charger",width=70,height=24,
                          font=ctk.CTkFont("Courier New",9),
                          fg_color=C("accent"),hover_color=C("accent_hover"),
                          text_color="#ffffff",corner_radius=4,
                          command=lambda n=name:self._profile_load(n)).pack(side="right",padx=4)
            ctk.CTkButton(row,text="✕",width=26,height=24,
                          font=ctk.CTkFont("Courier New",9),
                          fg_color="transparent",hover_color=C("ghost_del_hover"),
                          text_color=C("ghost_del_text"),corner_radius=4,
                          command=lambda n=name:self._profile_delete(n)).pack(side="right",padx=2)

    def _profile_load(self, name):
        self._apply_config(state.profiles[name]); self._log(f"Profil '{name}' charge.")

    def _profile_delete(self, name):
        del state.profiles[name]; self._profile_refresh()

    def _profile_export(self):
        if not state.licensed:
            messagebox.showinfo("Licence requise","Necessite une licence."); return
        path = filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("JSON","*.json")])
        if path:
            with open(path,"w",encoding="utf-8") as f: json.dump(state.profiles,f,indent=2,ensure_ascii=False)
            self._log(f"Exporte -> {path}")

    def _profile_import(self):
        if not state.licensed:
            messagebox.showinfo("Licence requise","Necessite une licence."); return
        path = filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if path:
            try:
                with open(path,encoding="utf-8") as f: state.profiles.update(json.load(f))
                self._profile_refresh()
            except Exception as e: messagebox.showerror("Erreur",str(e))

    # ── Status bar ────────────────────────────────────────────────────────────

    def _build_status_bar(self):
        sf = ctk.CTkFrame(self, corner_radius=8, height=50)
        sf.pack(fill="x", padx=16, pady=(8,0))
        sf.pack_propagate(False)
        self.status_dot = ctk.CTkLabel(sf, text="●", font=ctk.CTkFont(size=14))
        self.status_dot.pack(side="left", padx=(16,6), pady=14)
        self.status_label = ctk.CTkLabel(sf, text="En attente",
                                          font=ctk.CTkFont("Courier New",12,"bold"))
        self.status_label.pack(side="left", pady=14)
        self.counter_label = ctk.CTkLabel(sf, text="0 appuis",
                                           font=ctk.CTkFont("Courier New",10),
                                           text_color=C("accent"))
        self.counter_label.pack(side="right", padx=16)

        self.progress = ctk.CTkProgressBar(self, height=4,
                                            progress_color=C("accent"), corner_radius=0)
        self.progress.pack(fill="x", padx=16, pady=(0,2))
        self.progress.set(0)

        ir = ctk.CTkFrame(self, fg_color="transparent")
        ir.pack(fill="x", padx=16)
        self.time_label = ctk.CTkLabel(ir, text="Temps restant : —",
                                        font=ctk.CTkFont("Courier New",9))
        self.time_label.pack(side="left")
        self.next_label = ctk.CTkLabel(ir, text="Prochain appui : —",
                                        font=ctk.CTkFont("Courier New",9))
        self.next_label.pack(side="right")

    # ── Boutons ───────────────────────────────────────────────────────────────

    def _build_buttons(self):
        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(pady=10)
        self.btn_start = ctk.CTkButton(bf, text="▶  Demarrer", width=150, height=40,
                                        font=ctk.CTkFont("Courier New",13,"bold"),
                                        fg_color=C("success"), hover_color=C("success_hover"),
                                        text_color="#ffffff", corner_radius=8, command=self.start)
        self.btn_start.grid(row=0, column=0, padx=6)
        self.btn_pause = ctk.CTkButton(bf, text="⏸  Pause", width=130, height=40,
                                        font=ctk.CTkFont("Courier New",12,"bold"),
                                        fg_color=C("warning"), hover_color=C("warning_hover"),
                                        text_color="#ffffff", corner_radius=8,
                                        state="disabled", command=self.toggle_pause)
        self.btn_pause.grid(row=0, column=1, padx=6)
        self.btn_stop = ctk.CTkButton(bf, text="■  Arreter", width=130, height=40,
                                       font=ctk.CTkFont("Courier New",12,"bold"),
                                       fg_color=C("danger"), hover_color=C("danger_hover"),
                                       text_color="#ffffff", corner_radius=8,
                                       state="disabled", command=self.stop)
        self.btn_stop.grid(row=0, column=2, padx=6)

    # ── Log ───────────────────────────────────────────────────────────────────

    def _build_log(self):
        lf = ctk.CTkFrame(self, corner_radius=8)
        lf.pack(fill="both", expand=True, padx=16, pady=(0,14))
        ctk.CTkLabel(lf, text="JOURNAL", font=ctk.CTkFont("Courier New",9,"bold")).pack(
            anchor="w", padx=12, pady=(6,0))
        self.log_box = ctk.CTkTextbox(lf, font=ctk.CTkFont("Courier New",9),
                                       text_color=C("log_text"),
                                       border_width=0, state="disabled")
        self.log_box.pack(fill="both", expand=True, padx=8, pady=(2,8))

    def _log(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{ts}]  {msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    # ── Logique ───────────────────────────────────────────────────────────────

    def start(self):
        if not state.licensed and not state.demo_mode:
            self._show_license_window(); return
        if state.demo_mode and time.time() >= state.demo_end:
            self._demo_expired(); return
        if self.running: return
        if state.demo_mode: self.mode_var.set("Touche simple")
        self.running = True; self.paused = False
        self.presses_done = 0; self.start_time = time.time()
        self.next_press_at = time.time() + self.interval_var.get()
        self.btn_start.configure(state="disabled")
        self.btn_pause.configure(state="normal")
        self.btn_stop.configure(state="normal")
        self.status_dot.configure(text_color=C("success"))
        self.status_label.configure(text="En cours...")
        self._log(f"Demarre — {self.mode_var.get()} | {self.interval_var.get()}s")
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self._update_ui()

    def stop(self):
        self.running = False; self.paused = False
        self.btn_start.configure(state="normal")
        self.btn_pause.configure(state="disabled", text="⏸  Pause")
        self.btn_stop.configure(state="disabled")
        self.status_dot.configure(text_color="gray")
        self.status_label.configure(text="Arrete")
        self.progress.set(0)
        self.time_label.configure(text="Temps restant : —")
        self.next_label.configure(text="Prochain appui : —")
        self._log(f"Arrete — {self.presses_done} appuis.")

    def toggle_pause(self):
        if not self.paused:
            self.paused = True
            self.btn_pause.configure(text="▶  Reprendre")
            self.status_dot.configure(text_color=C("warning"))
            self.status_label.configure(text="En pause")
            self._log("Pause.")
        else:
            self.paused = False
            self.btn_pause.configure(text="⏸  Pause")
            self.status_dot.configure(text_color=C("success"))
            self.status_label.configure(text="En cours...")
            self._log("Reprise.")

    def _press_key(self, key_label):
        k = SPECIAL_KEYS.get(key_label, Key.caps_lock)
        keyboard_ctrl.press(k); keyboard_ctrl.release(k)

    def _run_loop(self):
        total_secs = (int(self.hours_var.get() or 0)*3600 +
                      int(self.mins_var.get() or 0)*60) if not self.infinite_var.get() else None
        if state.demo_mode:
            total_secs = max(0, state.demo_end - time.time())
        mode = "Touche simple" if state.demo_mode else self.mode_var.get()

        while self.running:
            if state.demo_mode and time.time() >= state.demo_end:
                self.after(0, self._demo_expired); break
            if total_secs and (time.time()-self.start_time) >= total_secs:
                self.after(0, self._finished); break
            if not self.paused and time.time() >= self.next_press_at:
                if self._in_schedule():
                    if mode == "Touche simple":
                        self._press_key(self.key_var.get()); self.presses_done += 1
                        lbl = self.key_var.get()
                        self.after(0, lambda l=lbl: self._log(f"Touche : {l}"))
                    else:
                        for kl,dm in state.sequence_items:
                            if not self.running: break
                            self._press_key(kl); self.presses_done += 1
                            self.after(0, lambda k=kl: self._log(f"Seq : {k}"))
                            time.sleep(dm/1000)
                else:
                    self.after(0, lambda: self._log("Hors plage — ignore."))
                self.next_press_at = time.time() + self.interval_var.get()
            time.sleep(0.25)

    def _update_ui(self):
        if not self.running: return
        elapsed = time.time()-self.start_time if self.start_time else 0
        total_secs = (int(self.hours_var.get() or 0)*3600 +
                      int(self.mins_var.get() or 0)*60) if not self.infinite_var.get() else None
        if state.demo_mode: total_secs = DEMO_SECONDS

        if total_secs and total_secs > 0:
            self.progress.set(min(1.0, elapsed/total_secs))
            rem = max(0, total_secs-elapsed)
            h,r = divmod(int(rem),3600); m,s = divmod(r,60)
            self.time_label.configure(text=f"Temps restant : {h:02d}h {m:02d}m {s:02d}s")
        else:
            self.progress.set((elapsed%10)/10)
            self.time_label.configure(text="Duree : infinie")

        self.counter_label.configure(text=f"{self.presses_done} appuis", text_color=C("accent"))
        if self.next_press_at and not self.paused:
            wait = max(0, self.next_press_at-time.time())
            self.next_label.configure(text=f"Prochain appui dans : {int(wait)}s")
        self.after(500, self._update_ui)

    def _finished(self):
        self.running = False
        self.status_dot.configure(text_color=C("accent"))
        self.status_label.configure(text="Termine")
        self.btn_start.configure(state="normal")
        self.btn_pause.configure(state="disabled", text="⏸  Pause")
        self.btn_stop.configure(state="disabled")
        self.progress.set(1.0)
        self._log(f"Session terminee — {self.presses_done} appuis.")
        messagebox.showinfo("KeyPresser Pro", f"Session terminee !\n{self.presses_done} appuis simules.")


if __name__ == "__main__":
    KeyPresserPro().mainloop()
