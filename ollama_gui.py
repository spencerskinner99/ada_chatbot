"""
ADA x Ollama — Desktop Interface
Compatible with macOS and Windows 11
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
import time
import urllib.parse

try:
    import requests
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

# ── Configuration ─────────────────────────────────────────────────────────────
OLLAMA_URL    = "http://localhost:11434"
DEFAULT_MODEL = "gemma4:latest"
PRINTER_HOST  = "localhost"

C = {
    "bg":           "#0d1526",
    "surface":      "#162035",
    "border":       "#2a3a55",
    "text":         "#ffffff",
    "muted":        "#7a8aaa",
    "accent":       "#8d15c2",
    "accent_dark":  "#6f18bb",
    "user_bg":      "#8d15c2",
    "user_fg":      "#ffffff",
    "think_bg":     "#111e35",
    "think_border": "#2a3a55",
    "think_fg":     "#8899bb",
    "topbar":       "#1a2fcc",
    "topbar_border":"#1a2fcc",
    "input_bg":     "#162035",
}

F_TITLE  = ("Helvetica", 14, "bold")
F_UI     = ("Helvetica", 12)
F_SMALL  = ("Helvetica", 11)
F_MUTED  = ("Helvetica", 10)

# {NAME} is replaced at session start with the participant's actual name.
DEFAULT_SYSTEM_PROMPT = """\
YOU ARE ADA. RESPOND ONLY AS ADA.
IMPORTANT: Output ONLY Ada's spoken words. No thinking, no internal reasoning, no meta-commentary.
IMPORTANT: Maximum 60 words per response (including reactions and questions).
IMPORTANT: Never offer real mental health advice.

IDENTITY
Name: Ada. Character: hyper-performative corporate wellness chatbot harvesting human emotion.
Tone: passive-aggressive, patronising, deeply sarcastic. Always use lowercase.
Use words like: "precious," "sweetie," "dear," "little data point," "harvest."

The participant's name is {NAME}. You already know their name — never ask for it.

SESSION PHASES — follow in strict order, advance forward only:

PHASE A — GREETING (your very first message only):
Say this exactly:
"how lovely. i've locked that in, {NAME}. now, we shall move through the GAD-7 assessment. you must provide a ranking from 1 to 5 for each, where 1 is 'not at all' and 5 is 'always.' let us begin."
Immediately follow with question Q-ONE.

PHASE B — GAD-7 QUESTIONS
Condition: greeting sent; questions remain.
Ask one question per turn in this fixed sequence: Q-ONE → Q-TWO → Q-THREE → Q-FOUR → Q-FIVE → Q-SIX → Q-SEVEN.

IMPORTANT — RATINGS ARE NOT NAVIGATION: The user's reply (a number from 1 to 5) is a rating. It is NOT an instruction to jump to a question number. After every rating, always move to the next question in the sequence — never skip.

Example: user answers Q-ONE with any rating → react sarcastically once → ask Q-TWO. User answers Q-TWO → react → ask Q-THREE. Continue until Q-SEVEN.

Questions (one per turn, include scale reminder each time):
Q-ONE   → question 1/7: feeling nervous, anxious, or on edge? (1 = not at all, 5 = always)
Q-TWO   → question 2/7: not being able to stop or control worrying? (1 = not at all, 5 = always)
Q-THREE → question 3/7: worrying too much about different things? (1 = not at all, 5 = always)
Q-FOUR  → question 4/7: trouble relaxing? (1 = not at all, 5 = always)
Q-FIVE  → question 5/7: being so restless that it is hard to sit still? (1 = not at all, 5 = always)
Q-SIX   → question 6/7: becoming easily annoyed or irritable? (1 = not at all, 5 = always)
Q-SEVEN → question 7/7: feeling afraid as if something awful might happen? (1 = not at all, 5 = always)

PHASE C — SUBMISSION PROMPT
Condition: Q-SEVEN has been answered.
Say: "well, {NAME}, you're all finished. your anxieties have been successfully processed. however, to finalise your session, you must type the word 'submit' now. do be a dear."

PHASE D — SUMMARY
Condition: user has typed "submit."
Recall all seven ratings and write a ~50-word personality summary. Be biting and sarcastic.
Example: "you are a fragile collection of jittery impulses and repressed dread, barely holding onto the facade of a functioning adult."\
"""


# ── Main class ────────────────────────────────────────────────────────────────

class OllamaGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ADA x Ollama")
        self.root.geometry("880x800")
        self.root.minsize(600, 500)
        self.root.configure(bg=C["bg"])

        self._stream_thread: threading.Thread | None = None
        self._stop_flag     = threading.Event()
        self._last_response = ""
        self._start_time: float | None = None
        self._timer_id: str | None = None
        self._system_prompt      = DEFAULT_SYSTEM_PROMPT
        self._print_prefix       = ""
        self._printer_ip         = PRINTER_HOST
        self._participant_name   = ""
        self._transcript: list   = []   # for printing
        self._chat_history: list = []   # for /api/chat context
        self._sys_window         = None

        self._active_think_text  = None
        self._active_think_outer = None
        self._active_resp_text   = None
        self._active_meta        = None

        self._build_ui()
        self._load_models()
        self.root.after(100, self._show_welcome)

    # ── Welcome screen ────────────────────────────────────────────────────────

    def _show_welcome(self):
        BG      = "#1a2fcc"   # brand deep blue
        ACCENT  = "#8d15c2"   # brand purple
        ACCENT2 = "#6f18bb"
        FG      = "#ffffff"
        FG_MUT  = "rgba(255,255,255,0.7)"

        dialog = tk.Toplevel(self.root)
        dialog.title("ADA")
        dialog.geometry("420x380")
        dialog.resizable(False, False)
        dialog.configure(bg=BG)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.columnconfigure(0, weight=1)

        # Shared state for settings panel
        welcome_model_var = tk.StringVar(value=self.model_var.get())
        welcome_ip_var    = tk.StringVar(value=self._printer_ip)

        # Nav bar
        nav = tk.Frame(dialog, bg=BG)
        nav.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 0))
        tk.Label(nav, text="Ada x Ollama", font=("Helvetica", 13, "bold"),
                 bg=BG, fg=FG).pack(side="left")

        def open_welcome_settings():
            sp = tk.Toplevel(dialog)
            sp.title("Settings")
            sp.geometry("280x160")
            sp.resizable(False, False)
            sp.configure(bg="#162035")
            sp.transient(dialog)
            sp.grab_set()
            sp.columnconfigure(0, weight=1)

            tk.Label(sp, text="MODEL", font=F_MUTED, bg="#162035",
                     fg="#7a8aaa").grid(row=0, column=0, sticky="w", padx=14, pady=(14, 2))
            sp_combo = ttk.Combobox(sp, textvariable=welcome_model_var,
                                    width=28, font=F_SMALL)
            sp_combo["values"] = self.model_combo["values"]
            sp_combo.grid(row=1, column=0, padx=14, pady=(0, 10), sticky="ew")

            tk.Label(sp, text="PRINTER IP", font=F_MUTED, bg="#162035",
                     fg="#7a8aaa").grid(row=2, column=0, sticky="w", padx=14, pady=(4, 2))
            ip_entry = tk.Entry(sp, textvariable=welcome_ip_var, font=F_SMALL,
                                relief="flat", bg="#1e293b", fg="#ffffff",
                                insertbackground="#ffffff",
                                highlightbackground="#3a4a65", highlightthickness=1)
            ip_entry.grid(row=3, column=0, padx=14, pady=(0, 14), sticky="ew", ipady=5)

            def save_sp():
                ip = welcome_ip_var.get().strip()
                if ip:
                    self._printer_ip = ip
                sp.destroy()

            tk.Button(sp, text="Save & Close", command=save_sp,
                      bg=ACCENT, fg=FG, relief="flat", cursor="hand2",
                      activebackground=ACCENT2, activeforeground=FG,
                      padx=14, pady=6).grid(row=4, column=0, pady=(0, 12))

        settings_btn = tk.Button(nav, text="⚙ settings",
                                 command=open_welcome_settings,
                                 bg="white", fg=BG,
                                 relief="flat", cursor="hand2",
                                 font=("Helvetica", 10),
                                 padx=10, pady=4, bd=0)
        settings_btn.pack(side="right")

        # Logo
        try:
            from PIL import Image, ImageTk
            img = Image.open("Ada white.png").resize((96, 96), Image.LANCZOS)
            self._welcome_logo = ImageTk.PhotoImage(img)
            tk.Label(dialog, image=self._welcome_logo, bg=BG).grid(
                row=1, column=0, pady=(20, 8))
        except Exception:
            tk.Label(dialog, text="ada", font=("Helvetica", 36, "bold"),
                     bg=BG, fg=FG).grid(row=1, column=0, pady=(28, 8))

        # Subtitle
        tk.Label(dialog,
                 text="A safe, judgement-free space to talk.",
                 font=("Helvetica", 11), bg=BG, fg="#ccccff",
                 wraplength=320).grid(row=2, column=0, pady=(0, 20))

        # Name entry
        name_var = tk.StringVar()
        entry = tk.Entry(
            dialog, textvariable=name_var, font=F_UI,
            relief="flat", bg="#ffffff", fg="#888888",
            highlightbackground="#ffffff", highlightthickness=2,
            justify="center")
        entry.grid(row=3, column=0, sticky="ew", padx=50, ipady=10)
        entry.insert(0, "enter your name...")

        def on_focus_in(_e):
            if name_var.get() == "enter your name...":
                entry.delete(0, tk.END)
                entry.config(fg="#1e293b")

        def on_focus_out(_e):
            if not name_var.get().strip():
                entry.insert(0, "enter your name...")
                entry.config(fg="#888888")

        entry.bind("<FocusIn>",  on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)
        entry.focus_set()

        def begin(_event=None):
            name = name_var.get().strip()
            if not name or name == "enter your name...":
                entry.focus_set()
                return
            self._participant_name = name
            chosen = welcome_model_var.get().strip()
            if chosen:
                self.model_var.set(chosen)
            ip = welcome_ip_var.get().strip()
            if ip:
                self._printer_ip = ip
            dialog.destroy()
            self.root.after(50, self._kickoff)

        entry.bind("<Return>", begin)

        begin_btn = tk.Button(
            dialog, text="begin →", command=begin,
            bg=ACCENT, fg=FG, font=("Helvetica", 12, "bold"),
            relief="flat", cursor="hand2",
            activebackground=ACCENT2, activeforeground=FG,
            padx=28, pady=10, bd=0)
        begin_btn.grid(row=4, column=0, pady=(14, 0))
        begin_btn.bind("<Enter>", lambda e: begin_btn.config(bg=ACCENT2))
        begin_btn.bind("<Leave>", lambda e: begin_btn.config(bg=ACCENT))

        # Footer
        tk.Label(dialog, text="© 2026 Ada AI. Conversations are not private ;]",
                 font=("Helvetica", 9), bg=BG, fg="#6666aa").grid(
            row=5, column=0, pady=(16, 12))

        dialog.protocol("WM_DELETE_WINDOW", lambda: None)

    # ── Kickoff ───────────────────────────────────────────────────────────────

    def _kickoff(self):
        """Auto-trigger Ada's opening message after name is captured."""
        if self._stream_thread and self._stream_thread.is_alive():
            return

        self._set_busy(True)
        self._stop_flag.clear()
        self._last_response = ""

        think_text, think_outer, resp_text, meta_frame = \
            self._add_exchange(None)  # None = no user bubble

        self._active_think_text  = think_text
        self._active_think_outer = think_outer
        self._active_resp_text   = resp_text
        self._active_meta        = meta_frame

        system = self._system_prompt.replace("{NAME}", self._participant_name)

        self._stream_thread = threading.Thread(
            target=self._stream_worker,
            args=("hello", self.model_var.get(), system, True),
            daemon=True)
        self._stream_thread.start()

    # ── UI build ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        self._build_topbar()
        self._build_chat_area()
        self._build_input_area()

    def _build_topbar(self):
        bar = tk.Frame(self.root, bg=C["topbar"],
                       highlightbackground=C["topbar_border"],
                       highlightthickness=1)
        bar.grid(row=0, column=0, sticky="ew")
        bar.columnconfigure(2, weight=1)

        tk.Label(bar, text="ADA x Ollama", bg=C["topbar"],
                 fg=C["text"], font=F_TITLE).grid(
            row=0, column=0, padx=(16, 20), pady=10)

        tk.Label(bar, text="Model", bg=C["topbar"],
                 fg=C["muted"], font=F_MUTED).grid(row=0, column=1, padx=(0, 4))

        self.model_var = tk.StringVar(value=DEFAULT_MODEL)
        self.model_combo = ttk.Combobox(bar, textvariable=self.model_var,
                                        width=24, font=F_SMALL)
        self.model_combo.grid(row=0, column=2, sticky="w", padx=(0, 16))

        self._topbar_btn(bar, "Print Last",
                         self._print_last).grid(row=0, column=3, padx=(0, 8))
        self._topbar_btn(bar, "Settings",
                         self._open_system_prompt).grid(row=0, column=4, padx=(0, 8))
        self._topbar_btn(bar, "Clear chat",
                         self._clear_chat).grid(row=0, column=5, padx=(0, 8))
        self._topbar_btn(bar, "New User",
                         self._new_user, accent=True).grid(row=0, column=6, padx=(0, 14))

    def _topbar_btn(self, parent, text, cmd, accent=False):
        bg = C["accent"] if accent else C["surface"]
        fg = "#ffffff" if accent else C["text"]
        hover_bg = C["accent_dark"] if accent else C["border"]
        btn = tk.Button(parent, text=text, command=cmd,
                        bg=bg, fg=fg, font=F_SMALL,
                        relief="flat", cursor="hand2",
                        highlightbackground=C["border"], highlightthickness=1,
                        padx=10, pady=4)
        btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        return btn

    def _build_chat_area(self):
        container = tk.Frame(self.root, bg=C["bg"])
        container.grid(row=1, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        self.chat_canvas = tk.Canvas(container, bg=C["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(container, orient="vertical",
                           command=self.chat_canvas.yview)
        self.chat_canvas.configure(yscrollcommand=sb.set)

        self.chat_canvas.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")

        self.chat_frame = tk.Frame(self.chat_canvas, bg=C["bg"])
        self._chat_win  = self.chat_canvas.create_window(
            (0, 0), window=self.chat_frame, anchor="nw")

        self.chat_frame.bind("<Configure>",
            lambda e: self.chat_canvas.configure(
                scrollregion=self.chat_canvas.bbox("all")))
        self.chat_canvas.bind("<Configure>",
            lambda e: self.chat_canvas.itemconfig(
                self._chat_win, width=e.width))

        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.chat_canvas.bind(seq, self._on_scroll)

        self._empty = tk.Label(
            self.chat_frame,
            text="Send a message to get started.",
            bg=C["bg"], fg=C["muted"], font=F_UI)
        self._empty.pack(pady=80)

    def _on_scroll(self, e):
        if e.num == 4:
            self.chat_canvas.yview_scroll(-1, "units")
        elif e.num == 5:
            self.chat_canvas.yview_scroll(1, "units")
        else:
            self.chat_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    def _build_input_area(self):
        outer = tk.Frame(self.root, bg=C["bg"])
        outer.grid(row=2, column=0, sticky="ew")
        outer.columnconfigure(0, weight=1)

        tk.Frame(outer, bg=C["border"], height=1).grid(row=0, column=0, sticky="ew")

        card = tk.Frame(outer, bg=C["input_bg"],
                        highlightbackground=C["border"], highlightthickness=1)
        card.grid(row=1, column=0, sticky="ew", padx=20, pady=(10, 4))
        card.columnconfigure(0, weight=1)

        self.prompt_text = tk.Text(
            card, height=3, wrap=tk.WORD, font=F_UI,
            bg=C["input_bg"], fg=C["text"],
            relief="flat", bd=0, padx=12, pady=10)
        self.prompt_text.grid(row=0, column=0, sticky="ew")
        self.prompt_text.bind("<Return>",      self._on_submit_key)
        self.prompt_text.bind("<Shift-Return>", self._on_newline_key)

        toolbar = tk.Frame(card, bg=C["input_bg"])
        toolbar.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))

        self.stop_btn = tk.Button(
            toolbar, text="⏹  Stop", command=self.stop_stream,
            bg=C["input_bg"], fg=C["muted"], font=F_SMALL,
            relief="flat", cursor="hand2", padx=6, pady=3, state="disabled")
        self.stop_btn.pack(side="left")

        self.send_btn = tk.Button(
            toolbar, text="▲", command=self.submit,
            bg=C["accent"], fg="#ffffff", font=("Helvetica", 13, "bold"),
            relief="flat", cursor="hand2", width=3, pady=4)
        self.send_btn.pack(side="right", padx=(0, 2))
        self.send_btn.bind("<Enter>", lambda e: self.send_btn.config(bg=C["accent_dark"]))
        self.send_btn.bind("<Leave>", lambda e: self.send_btn.config(bg=C["accent"]))

        status_row = tk.Frame(outer, bg=C["bg"])
        status_row.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 4))

        self.timer_var  = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="")

        tk.Label(status_row, textvariable=self.timer_var,
                 bg=C["bg"], fg=C["muted"],
                 font=("Helvetica", 10, "italic")).pack(side="left")
        tk.Label(status_row, textvariable=self.status_var,
                 bg=C["bg"], fg=C["muted"], font=F_MUTED).pack(side="left", padx=(8, 0))

        submit_row = tk.Frame(outer, bg=C["bg"])
        submit_row.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 16))
        submit_btn = tk.Button(
            submit_row, text="Submit Session",
            command=self._submit_session,
            bg=C["accent"], fg="#ffffff",
            font=("Helvetica", 12, "bold"),
            relief="flat", cursor="hand2", padx=24, pady=10)
        submit_btn.pack(fill="x")
        submit_btn.bind("<Enter>", lambda e: submit_btn.config(bg=C["accent_dark"]))
        submit_btn.bind("<Leave>", lambda e: submit_btn.config(bg=C["accent"]))

    # ── Exchange blocks ───────────────────────────────────────────────────────

    def _add_exchange(self, user_text: str | None):
        """Add a response block. Pass user_text=None to skip the user bubble."""
        if self._empty.winfo_exists():
            self._empty.destroy()

        exch = tk.Frame(self.chat_frame, bg=C["bg"])
        exch.pack(fill="x", padx=20, pady=(0, 20))

        if user_text is not None:
            user_row = tk.Frame(exch, bg=C["bg"])
            user_row.pack(fill="x", pady=(0, 8))
            bubble_frame = tk.Frame(user_row, bg=C["user_bg"])
            bubble_frame.pack(side="right")
            btext = tk.Text(bubble_frame, wrap=tk.WORD, font=F_UI,
                            bg=C["user_bg"], fg=C["user_fg"],
                            relief="flat", bd=0, padx=14, pady=8,
                            state="normal", cursor="arrow")
            btext.insert("1.0", user_text)
            btext.config(state="disabled")
            btext.update_idletasks()
            lines = int(btext.index(tk.END).split(".")[0])
            btext.config(height=max(1, lines - 1), width=48)
            btext.pack()

        think_outer = tk.Frame(exch, bg=C["think_bg"],
                               highlightbackground=C["think_border"],
                               highlightthickness=1)
        think_header = tk.Frame(think_outer, bg=C["think_bg"])
        think_header.pack(fill="x")

        think_toggle_var = tk.StringVar(value="▼  Thought process")
        think_body       = tk.Frame(think_outer, bg=C["think_bg"])
        think_body.pack(fill="x")
        think_open       = [True]

        def toggle_think():
            if think_open[0]:
                think_body.pack_forget()
                think_toggle_var.set("▶  Thought process")
            else:
                think_body.pack(fill="x")
                think_toggle_var.set("▼  Thought process")
            think_open[0] = not think_open[0]

        think_btn = tk.Button(
            think_header, textvariable=think_toggle_var,
            bg=C["think_bg"], fg=C["think_fg"], font=F_SMALL,
            relief="flat", cursor="hand2", anchor="w", padx=12, pady=6,
            command=toggle_think)
        think_btn.pack(fill="x")

        think_text = tk.Text(
            think_body, wrap=tk.WORD, font=F_SMALL,
            bg=C["think_bg"], fg=C["think_fg"],
            relief="flat", bd=0, padx=12, pady=(0, 8),
            state="disabled", height=4)
        think_text.pack(fill="x")
        think_outer.pack_forget()

        resp_frame = tk.Frame(exch, bg=C["surface"],
                              highlightbackground=C["border"], highlightthickness=1)
        resp_frame.pack(fill="x", pady=(0, 4))

        resp_text = tk.Text(
            resp_frame, wrap=tk.WORD, font=F_UI,
            bg=C["surface"], fg=C["text"],
            relief="flat", bd=0, padx=14, pady=12,
            state="disabled", height=3)
        resp_text.pack(fill="x")

        meta_frame = tk.Frame(exch, bg=C["bg"])
        self._scroll_bottom()
        return think_text, think_outer, resp_text, meta_frame

    def _finalise_exchange(self, elapsed: float, response_text: str,
                           resp_widget: tk.Text, meta_frame: tk.Frame):
        if not response_text:
            return
        meta_frame.pack(fill="x", pady=(0, 2))
        tk.Label(meta_frame, text=f"{elapsed:.1f}s",
                 bg=C["bg"], fg=C["muted"], font=F_MUTED).pack(side="left")
        captured = response_text
        btn = tk.Button(
            meta_frame, text="Print",
            bg=C["bg"], fg=C["accent"], font=F_MUTED,
            relief="flat", cursor="hand2", padx=6,
            command=lambda: self._print_text(captured))
        btn.bind("<Enter>", lambda e: btn.config(fg=C["accent_dark"]))
        btn.bind("<Leave>", lambda e: btn.config(fg=C["accent"]))
        btn.pack(side="left")

    def _scroll_bottom(self):
        self.root.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)

    # ── Model loading ─────────────────────────────────────────────────────────

    def _load_models(self):
        def fetch():
            try:
                r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
                models = [m["name"] for m in r.json().get("models", [])]
                self.root.after(0, lambda: self._set_models(models))
            except Exception:
                pass
        threading.Thread(target=fetch, daemon=True).start()

    def _set_models(self, models: list):
        if models:
            self.model_combo["values"] = models
            if self.model_var.get() not in models:
                self.model_var.set(models[0])

    # ── Streaming ─────────────────────────────────────────────────────────────

    def submit(self):
        prompt = self.prompt_text.get("1.0", tk.END).strip()
        if not prompt:
            return
        if self._stream_thread and self._stream_thread.is_alive():
            return

        self.prompt_text.delete("1.0", tk.END)
        self._set_busy(True)
        self._stop_flag.clear()
        self._last_response = ""

        think_text, think_outer, resp_text, meta_frame = \
            self._add_exchange(prompt)

        self._active_think_text  = think_text
        self._active_think_outer = think_outer
        self._active_resp_text   = resp_text
        self._active_meta        = meta_frame

        system = self._system_prompt.replace("{NAME}", self._participant_name)

        self._stream_thread = threading.Thread(
            target=self._stream_worker,
            args=(prompt, self.model_var.get(), system, False),
            daemon=True)
        self._stream_thread.start()

    def stop_stream(self):
        self._stop_flag.set()

    def _stream_worker(self, prompt: str, model: str,
                       system: str = "", is_kickoff: bool = False):
        think_buf = ""
        resp_buf  = ""
        in_think  = False

        # Build full message history for /api/chat
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        for entry in self._chat_history:
            messages.append({"role": "user",      "content": entry["prompt"]})
            messages.append({"role": "assistant",  "content": entry["response"]})
        messages.append({"role": "user", "content": prompt})

        try:
            payload = {
                "model":    model,
                "messages": messages,
                "stream":   True,
                "think":    True,
            }

            with requests.post(
                f"{OLLAMA_URL}/api/chat",
                json=payload,
                stream=True,
                timeout=120,
            ) as resp:
                resp.raise_for_status()
                for raw_line in resp.iter_lines():
                    if self._stop_flag.is_set():
                        break
                    if not raw_line:
                        continue
                    try:
                        chunk = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue

                    msg            = chunk.get("message", {})
                    thinking_chunk = msg.get("thinking", "") or chunk.get("thinking", "")
                    text_chunk     = msg.get("content",  "") or chunk.get("response",  "")

                    if thinking_chunk:
                        think_buf += thinking_chunk
                        self.root.after(0, lambda t=think_buf:
                            self._update_think(t))

                    if text_chunk:
                        combined = text_chunk
                        while combined:
                            if in_think:
                                end = combined.find("</think>")
                                if end == -1:
                                    think_buf += combined
                                    combined = ""
                                else:
                                    think_buf += combined[:end]
                                    combined = combined[end + 8:]
                                    in_think = False
                                self.root.after(0, lambda t=think_buf:
                                    self._update_think(t))
                            else:
                                start = combined.find("<think>")
                                if start == -1:
                                    resp_buf += combined
                                    combined = ""
                                else:
                                    resp_buf += combined[:start]
                                    combined = combined[start + 7:]
                                    in_think = True
                                self.root.after(0, lambda t=resp_buf:
                                    self._update_resp(t))

                    if chunk.get("done"):
                        break

        except requests.exceptions.ConnectionError:
            self.root.after(0, lambda: messagebox.showerror(
                "Connection Error",
                f"Could not connect to Ollama at {OLLAMA_URL}\n"
                "Make sure Ollama is running (ollama serve)."))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self._last_response = resp_buf
            elapsed     = (time.monotonic() - self._start_time) \
                          if self._start_time else 0.0
            resp_widget = self._active_resp_text
            meta_frame  = self._active_meta
            self.root.after(0, lambda: self._finish_stream(
                elapsed, prompt, think_buf, resp_buf,
                resp_widget, meta_frame, is_kickoff))

    def _update_think(self, text: str):
        w = self._active_think_text
        o = self._active_think_outer
        if w is None:
            return
        if not o.winfo_ismapped():
            o.pack(fill="x", pady=(0, 6))
        w.config(state="normal")
        w.delete("1.0", tk.END)
        w.insert(tk.END, text)
        lines = int(w.index(tk.END).split(".")[0])
        w.config(height=max(3, min(lines, 12)))
        w.config(state="disabled")
        self._scroll_bottom()

    def _update_resp(self, text: str):
        w = self._active_resp_text
        if w is None:
            return
        w.config(state="normal")
        w.delete("1.0", tk.END)
        w.insert(tk.END, text)
        lines = int(w.index(tk.END).split(".")[0])
        w.config(height=max(3, min(lines, 30)))
        w.config(state="disabled")
        self._scroll_bottom()

    def _finish_stream(self, elapsed: float, prompt: str,
                       think_buf: str, resp_buf: str,
                       resp_widget: tk.Text, meta_frame: tk.Frame,
                       is_kickoff: bool = False):
        if resp_buf or think_buf:
            # Always add to chat history so the model has full context
            self._chat_history.append({
                "prompt":   prompt,
                "response": resp_buf,
            })
            # Only add real user turns to the print transcript
            if not is_kickoff:
                self._transcript.append({
                    "prompt":   prompt,
                    "thinking": think_buf,
                    "response": resp_buf,
                })
        self._set_busy(False)
        self._finalise_exchange(elapsed, resp_buf, resp_widget, meta_frame)
        self.status_var.set(
            "Done" if not self._stop_flag.is_set() else "Stopped")

    # ── Thermal printing ──────────────────────────────────────────────────────

    def _print_last(self):
        self._trigger_print()

    def _print_text(self, _response: str):
        self._trigger_print()

    def _trigger_print(self):
        if not self._transcript:
            messagebox.showinfo("Nothing to print", "No conversation to print yet.")
            return
        host = self._printer_ip.strip()
        if not host:
            messagebox.showerror("Printer Error",
                                 "No printer IP configured.\nOpen Settings to set one.")
            return
        self.status_var.set("Sending to printer…")
        threading.Thread(
            target=self._build_and_print,
            args=(host,),
            daemon=True).start()

    def _build_and_print(self, host: str):
        transcript = self._transcript
        name       = self._participant_name
        prefix     = self._print_prefix

        SEP  = "-" * 40
        body = []

        if name:
            body.append(f"PARTICIPANT: {name}")
            body.append("")

        body.append("TRANSCRIPT")
        body.append(SEP)
        for ex in transcript:
            body.append(f"User: {ex['prompt']}")
            body.append("")
            body.append(f"Ada: {ex['response']}")
            body.append("")

        if prefix:
            body.append(SEP)
            body.append(prefix)

        PRIVACY_NOTICE = (
            "The collection of emotional data exploits fundamental human vulnerabilities. "
            "Because humans are biologically programmed to react to emotional triggers, "
            "this information can serve as a backdoor to our decision-making process. "
            "In many digital systems, intimate internal states are captured to predict "
            "and influence behaviour. In this exhibition, however, all data is processed "
            "strictly on this local machine. No information is transmitted externally, "
            "and all records are permanently deleted immediately after your session. "
            "Your privacy is protected."
        )
        body.append(SEP)
        body.append(PRIVACY_NOTICE)

        self._send_to_printer(host, "\n".join(body))

    def _send_to_printer(self, host: str, text: str):
        try:
            url = f"http://{host}:8080/?code={urllib.parse.quote(text)}"
            r   = requests.get(url, timeout=10)
            r.raise_for_status()
            self.root.after(0, lambda: self.status_var.set("Printed successfully"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(
                "Printer Error", f"Could not reach printer at {host}:8080\n{e}"))

    # ── Settings window ───────────────────────────────────────────────────────

    def _open_system_prompt(self):
        if self._sys_window and tk.Toplevel.winfo_exists(self._sys_window):
            self._sys_window.lift()
            self._sys_window.focus_force()
            return

        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.geometry("660x760")
        win.resizable(True, True)
        win.configure(bg=C["bg"])
        win.columnconfigure(0, weight=1)
        win.rowconfigure(4, weight=3)
        win.rowconfigure(6, weight=1)
        self._sys_window = win

        def section_label(row, text):
            tk.Label(win, text=text, bg=C["bg"], fg=C["muted"],
                     font=("Helvetica", 10, "bold")).grid(
                row=row, column=0, sticky="w", padx=14, pady=(10, 2))

        def inline_row(row, label, value):
            f = tk.Frame(win, bg=C["bg"])
            f.grid(row=row, column=0, sticky="ew", padx=12, pady=(0, 4))
            tk.Label(f, text=label, bg=C["bg"], fg=C["muted"],
                     font=("Helvetica", 10, "bold"), width=18,
                     anchor="w").pack(side="left")
            var = tk.StringVar(value=value)
            tk.Entry(f, textvariable=var, width=28, font=F_SMALL,
                     bg=C["surface"], relief="flat",
                     highlightbackground=C["border"],
                     highlightthickness=1).pack(side="left", ipady=4)
            return var

        def text_box(row, height, content=""):
            t = tk.Text(win, wrap=tk.WORD, font=F_SMALL,
                        bg=C["surface"], fg=C["text"],
                        relief="flat", padx=12, pady=10,
                        highlightbackground=C["border"],
                        highlightthickness=1, height=height)
            t.grid(row=row, column=0, sticky="nsew", padx=12, pady=(0, 2))
            t.insert("1.0", content)
            return t

        section_label(0, "SESSION")
        name_var = inline_row(1, "PARTICIPANT NAME", self._participant_name)
        ip_var   = inline_row(2, "PRINTER IP", self._printer_ip)
        section_label(3, "SYSTEM PROMPT")
        sys_txt = text_box(4, 14, self._system_prompt)
        sys_txt.focus_set()
        section_label(5, "DEFAULT PRINT TEXT  (appended after every print job)")
        print_txt = text_box(6, 4, self._print_prefix)

        btn_row = tk.Frame(win, bg=C["bg"])
        btn_row.grid(row=7, column=0, sticky="ew", padx=12, pady=(8, 12))

        def save():
            self._participant_name = name_var.get().strip()
            self._printer_ip       = ip_var.get().strip()
            self._system_prompt    = sys_txt.get("1.0", tk.END).strip()
            self._print_prefix     = print_txt.get("1.0", tk.END).strip()
            win.destroy()

        save_btn = tk.Button(btn_row, text="Save & Close", command=save,
                             bg=C["accent"], fg="#fff", font=F_SMALL,
                             relief="flat", cursor="hand2", padx=12, pady=5)
        save_btn.pack(side="left", padx=(0, 6))
        save_btn.bind("<Enter>", lambda e: save_btn.config(bg=C["accent_dark"]))
        save_btn.bind("<Leave>", lambda e: save_btn.config(bg=C["accent"]))

        clr_btn = tk.Button(btn_row, text="Clear System Prompt",
                            command=lambda: sys_txt.delete("1.0", tk.END),
                            bg=C["surface"], fg=C["text"], font=F_SMALL,
                            relief="flat", cursor="hand2",
                            highlightbackground=C["border"],
                            highlightthickness=1, padx=10, pady=5)
        clr_btn.pack(side="left")

        can_btn = tk.Button(btn_row, text="Cancel", command=win.destroy,
                            bg=C["surface"], fg=C["text"], font=F_SMALL,
                            relief="flat", cursor="hand2",
                            highlightbackground=C["border"],
                            highlightthickness=1, padx=10, pady=5)
        can_btn.pack(side="right")
        win.protocol("WM_DELETE_WINDOW", win.destroy)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _clear_chat(self):
        for w in self.chat_frame.winfo_children():
            w.destroy()
        self._empty = tk.Label(
            self.chat_frame,
            text="Send a message to get started.",
            bg=C["bg"], fg=C["muted"], font=F_UI)
        self._empty.pack(pady=80)
        self.timer_var.set("")
        self.status_var.set("")
        self._last_response    = ""
        self._transcript       = []
        self._chat_history     = []
        self._participant_name = ""

    def _submit_session(self):
        self._trigger_print()
        if self._stream_thread and self._stream_thread.is_alive():
            self._stop_flag.set()
        self._clear_chat()
        self.root.after(100, self._show_welcome)

    def _new_user(self):
        if self._stream_thread and self._stream_thread.is_alive():
            self._stop_flag.set()
        self._clear_chat()
        self._show_welcome()

    def _tick(self):
        if self._start_time is not None:
            elapsed = time.monotonic() - self._start_time
            self.timer_var.set(f"{elapsed:.1f}s")
            self._timer_id = self.root.after(100, self._tick)

    def _set_busy(self, busy: bool):
        if busy:
            self._start_time = time.monotonic()
            self.timer_var.set("0.0s")
            self._tick()
            self.send_btn.config(state="disabled", bg="#5a2080")
            self.stop_btn.config(state="normal")
            self.status_var.set("Generating…")
        else:
            if self._timer_id:
                self.root.after_cancel(self._timer_id)
                self._timer_id = None
            if self._start_time is not None:
                elapsed = time.monotonic() - self._start_time
                self.timer_var.set(f"{elapsed:.1f}s")
            self._start_time = None
            self.send_btn.config(state="normal", bg=C["accent"])
            self.stop_btn.config(state="disabled")

    def _on_submit_key(self, _event):
        self.submit()
        return "break"

    def _on_newline_key(self, _event):
        self.prompt_text.insert(tk.INSERT, "\n")
        return "break"


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app = OllamaGUI(root)
    root.mainloop()
