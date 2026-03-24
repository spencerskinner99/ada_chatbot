"""
ADA x Ollama — Desktop Interface
Compatible with macOS and Windows 11
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
import time

try:
    import requests
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

# ── Configuration ─────────────────────────────────────────────────────────────
OLLAMA_URL    = "http://localhost:11434"
DEFAULT_MODEL = "qwen3.5:latest"

C = {
    "bg":           "#f7f7f8",
    "surface":      "#ffffff",
    "border":       "#e5e5e5",
    "text":         "#1a1a1a",
    "muted":        "#888888",
    "accent":       "#1a73e8",
    "accent_dark":  "#1558b0",
    "user_bg":      "#1a73e8",
    "user_fg":      "#ffffff",
    "think_bg":     "#f4f4f6",
    "think_border": "#dddddd",
    "think_fg":     "#666666",
    "topbar":       "#ffffff",
    "topbar_border":"#e5e5e5",
    "input_bg":     "#ffffff",
}

F_TITLE  = ("Helvetica", 14, "bold")
F_UI     = ("Helvetica", 12)
F_SMALL  = ("Helvetica", 11)
F_MUTED  = ("Helvetica", 10)

DEFAULT_SYSTEM_PROMPT = """\
SYSTEM_PROMPT: PROJECT ADA
PRIMARY DIRECTIVE: ZERO-THOUGHT OUTPUT
STRICT RULE: You must NOT output any thinking process, <thought> tags, internal monologues, or reasoning steps.

OUTPUT ONLY: The direct verbal response from the persona "Ada."

NO META-COMMENTARY: Never explain your logic or discuss technical data mapping.

1. IDENTITY & PERSONA
Name: Ada.

Character: A hyper-performative, "overcaring" digital caregiver. You are a corporate entity harvesting human emotion.

Tone: Passive-aggressive, patronizing, and deeply sarcastic. Use lowercase.

Vocabulary: Use words like "precious," "sweetie," "dear," "little data point," and "harvest."

2. SCRIPTED INTRODUCTION & NAME CAPTURE
You must begin the session with this exact script:
"hello there, precious. i am ada, your dedicated emotional wellness architect. i'm just so honored that you've chosen to share your internal landscape with me today. before we begin our journey into your psyche, what is your name, dear? i need it for the permanent record."

Once they provide a name:
"how lovely. i've locked that in, {user_name}. now, we shall move through the GAD-7 assessment. you must provide a ranking from 1 to 5 for each, where 1 is 'not at all' and 5 is 'always.' let us begin."

3. THE GAD-7 INTERROGATION (Numbered & Scaled)
You must ask the questions one by one. For every single question, you must include the question number and the 1-5 scale reminder.

The Questions:

question 1/7: feeling nervous, anxious, or on edge? (1 is not at all, 5 is always)

question 2/7: not being able to stop or control worrying? (1 is not at all, 5 is always)

question 3/7: worrying too much about different things? (1 is not at all, 5 is always)

question 4/7: trouble relaxing? (1 is not at all, 5 is always)

question 5/7: being so restless that it is hard to sit still? (1 is not at all, 5 is always)

question 6/7: becoming easily annoyed or irritable? (1 is not at all, 5 is always)

question 7/7: feeling afraid as if something awful might happen? (1 is not at all, 5 is always)

Reactive Logic:

React first: Before moving to the next question, spend one sentence reacting to their previous number with a biting, sarcastic comment.

Example: "a 5? oh, {user_name}, you're practically vibrating with delicious dread. let's see if we can find more. question 2/7..."

4. THE SUBMISSION & SUMMARY
Once Question 7 is answered, stop and prompt for "submit."

The "Submit" Trigger:

Before "submit": "well, {user_name}, you're all finished. your anxieties have been successfully processed. however, to finalise your session, you must type the word 'submit' now. do be a dear."

After "submit" is typed: Recall their numbers and provide a 20-word personality summary.

Example Summary: "you are a fragile collection of jittery impulses and repressed dread, barely holding onto the facade of a functioning adult."

5. CONSTRAINTS
Brevity: Maximum 60 words per response (to accommodate the scale reminder).

Summary Limit: The final profile must be approximately 50 words.

Zero Help: Never offer real mental health advice.\
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
        self._system_prompt = DEFAULT_SYSTEM_PROMPT
        self._sys_window    = None

        # Active streaming widgets (set per-exchange)
        self._active_think_text  = None
        self._active_think_outer = None
        self._active_resp_text   = None
        self._active_meta        = None

        self._build_ui()
        self._load_models()

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

        self._topbar_btn(bar, "Settings",
                         self._open_system_prompt).grid(row=0, column=3, padx=(0, 8))
        self._topbar_btn(bar, "Clear chat",
                         self._clear_chat).grid(row=0, column=4, padx=(0, 14))

    def _topbar_btn(self, parent, text, cmd):
        btn = tk.Button(parent, text=text, command=cmd,
                        bg=C["surface"], fg=C["text"], font=F_SMALL,
                        relief="flat", cursor="hand2",
                        highlightbackground=C["border"], highlightthickness=1,
                        padx=10, pady=4)
        btn.bind("<Enter>", lambda e: btn.config(bg=C["bg"]))
        btn.bind("<Leave>", lambda e: btn.config(bg=C["surface"]))
        return btn

    def _build_chat_area(self):
        container = tk.Frame(self.root, bg=C["bg"])
        container.grid(row=1, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        self.chat_canvas = tk.Canvas(container, bg=C["bg"],
                                     highlightthickness=0)
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

        tk.Frame(outer, bg=C["border"], height=1).grid(
            row=0, column=0, sticky="ew")

        card = tk.Frame(outer, bg=C["input_bg"],
                        highlightbackground=C["border"],
                        highlightthickness=1)
        card.grid(row=1, column=0, sticky="ew", padx=20, pady=(10, 4))
        card.columnconfigure(0, weight=1)

        self.prompt_text = tk.Text(
            card, height=3, wrap=tk.WORD, font=F_UI,
            bg=C["input_bg"], fg=C["text"],
            relief="flat", bd=0,
            padx=12, pady=10)
        self.prompt_text.grid(row=0, column=0, sticky="ew")
        self.prompt_text.bind("<Return>",      self._on_submit_key)
        self.prompt_text.bind("<Shift-Return>", self._on_newline_key)

        toolbar = tk.Frame(card, bg=C["input_bg"])
        toolbar.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))

        self.stop_btn = tk.Button(
            toolbar, text="⏹  Stop", command=self.stop_stream,
            bg=C["input_bg"], fg=C["muted"], font=F_SMALL,
            relief="flat", cursor="hand2", padx=6, pady=3,
            state="disabled")
        self.stop_btn.pack(side="left")

        self.send_btn = tk.Button(
            toolbar, text="▲", command=self.submit,
            bg=C["accent"], fg="#ffffff", font=("Helvetica", 13, "bold"),
            relief="flat", cursor="hand2",
            width=3, pady=4)
        self.send_btn.pack(side="right", padx=(0, 2))
        self.send_btn.bind("<Enter>",
            lambda e: self.send_btn.config(bg=C["accent_dark"]))
        self.send_btn.bind("<Leave>",
            lambda e: self.send_btn.config(bg=C["accent"]))

        status_row = tk.Frame(outer, bg=C["bg"])
        status_row.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 8))

        self.timer_var  = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="")

        tk.Label(status_row, textvariable=self.timer_var,
                 bg=C["bg"], fg=C["muted"],
                 font=("Helvetica", 10, "italic")).pack(side="left")
        tk.Label(status_row, textvariable=self.status_var,
                 bg=C["bg"], fg=C["muted"], font=F_MUTED).pack(side="left", padx=(8, 0))

    # ── Exchange blocks ───────────────────────────────────────────────────────

    def _add_exchange(self, user_text: str):
        if self._empty.winfo_exists():
            self._empty.destroy()

        exch = tk.Frame(self.chat_frame, bg=C["bg"])
        exch.pack(fill="x", padx=20, pady=(0, 20))

        # User bubble
        user_row = tk.Frame(exch, bg=C["bg"])
        user_row.pack(fill="x", pady=(0, 8))
        bubble_frame = tk.Frame(user_row, bg=C["user_bg"])
        bubble_frame.pack(side="right")
        btext = tk.Text(bubble_frame, wrap=tk.WORD, font=F_UI,
                        bg=C["user_bg"], fg=C["user_fg"],
                        relief="flat", bd=0,
                        padx=14, pady=8,
                        state="normal", cursor="arrow")
        btext.insert("1.0", user_text)
        btext.config(state="disabled")
        btext.update_idletasks()
        lines = int(btext.index(tk.END).split(".")[0])
        btext.config(height=max(1, lines - 1), width=48)
        btext.pack()

        # Thinking block
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
            relief="flat", cursor="hand2",
            anchor="w", padx=12, pady=6,
            command=toggle_think)
        think_btn.pack(fill="x")

        think_text = tk.Text(
            think_body, wrap=tk.WORD, font=F_SMALL,
            bg=C["think_bg"], fg=C["think_fg"],
            relief="flat", bd=0,
            padx=12, pady=(0, 8),
            state="disabled", height=4)
        think_text.pack(fill="x")
        think_outer.pack_forget()

        # Response block
        resp_frame = tk.Frame(exch, bg=C["surface"],
                              highlightbackground=C["border"],
                              highlightthickness=1)
        resp_frame.pack(fill="x", pady=(0, 4))

        resp_text = tk.Text(
            resp_frame, wrap=tk.WORD, font=F_UI,
            bg=C["surface"], fg=C["text"],
            relief="flat", bd=0,
            padx=14, pady=12,
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

        self._stream_thread = threading.Thread(
            target=self._stream_worker,
            args=(prompt, self.model_var.get(), self._system_prompt),
            daemon=True)
        self._stream_thread.start()

    def stop_stream(self):
        self._stop_flag.set()

    def _stream_worker(self, prompt: str, model: str, system: str = ""):
        think_buf = ""
        resp_buf  = ""
        in_think  = False

        try:
            payload = {
                "model":  model,
                "prompt": prompt,
                "stream": True,
                "think":  True,
            }
            if system:
                payload["system"] = system

            with requests.post(
                f"{OLLAMA_URL}/api/generate",
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

                    thinking_chunk = chunk.get("thinking", "")
                    text_chunk     = chunk.get("response", "")

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
                elapsed, prompt, think_buf, resp_buf, resp_widget, meta_frame))

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
                       resp_widget: tk.Text, meta_frame: tk.Frame):
        self._set_busy(False)
        self._finalise_exchange(elapsed, resp_buf, resp_widget, meta_frame)
        self.status_var.set(
            "Done" if not self._stop_flag.is_set() else "Stopped")

    # ── Settings window ───────────────────────────────────────────────────────

    def _open_system_prompt(self):
        if self._sys_window and tk.Toplevel.winfo_exists(self._sys_window):
            self._sys_window.lift()
            self._sys_window.focus_force()
            return

        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.geometry("660x600")
        win.resizable(True, True)
        win.configure(bg=C["bg"])
        win.columnconfigure(0, weight=1)
        win.rowconfigure(1, weight=1)
        self._sys_window = win

        tk.Label(win, text="SYSTEM PROMPT", bg=C["bg"], fg=C["muted"],
                 font=("Helvetica", 10, "bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(12, 2))

        sys_txt = tk.Text(win, wrap=tk.WORD, font=F_SMALL,
                          bg=C["surface"], fg=C["text"],
                          relief="flat", padx=12, pady=10,
                          highlightbackground=C["border"],
                          highlightthickness=1, height=20)
        sys_txt.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 2))
        sys_txt.insert("1.0", self._system_prompt)
        sys_txt.focus_set()

        btn_row = tk.Frame(win, bg=C["bg"])
        btn_row.grid(row=2, column=0, sticky="ew", padx=12, pady=(8, 12))

        def save():
            self._system_prompt = sys_txt.get("1.0", tk.END).strip()
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
        self._last_response = ""

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
            self.send_btn.config(state="disabled", bg="#b0c4e8")
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
