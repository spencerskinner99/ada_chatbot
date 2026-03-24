"""
ADA x Ollama — Desktop Interface
Compatible with macOS and Windows 11
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json

try:
    import requests
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

# ── Configuration ─────────────────────────────────────────────────────────────
OLLAMA_URL    = "http://localhost:11434"
DEFAULT_MODEL = "qwen3.5:latest"


# ── Main class ────────────────────────────────────────────────────────────────

class OllamaGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ADA x Ollama")
        self.root.geometry("800x700")
        self.root.configure(bg="#f0f0f0")
        self.root.columnconfigure(0, weight=1)
        for r, w in enumerate([0, 1, 1, 0, 0, 0]):
            self.root.rowconfigure(r, weight=w)

        self._stop_flag = threading.Event()
        self._build_ui()
        self._load_models()

    # ── UI build ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Top bar: title + model selector
        bar = tk.Frame(self.root, bg="#ffffff", pady=8,
                       relief="flat", highlightbackground="#e0e0e0",
                       highlightthickness=1)
        bar.grid(row=0, column=0, sticky="ew")
        tk.Label(bar, text="ADA x Ollama", bg="#ffffff",
                 font=("Helvetica", 14, "bold")).pack(side="left", padx=12)
        tk.Label(bar, text="Model:", bg="#ffffff").pack(side="left")
        self.model_var = tk.StringVar(value=DEFAULT_MODEL)
        self.model_combo = ttk.Combobox(bar, textvariable=self.model_var, width=24)
        self.model_combo.pack(side="left", padx=4)

        # Thinking panel
        tk.Label(self.root, text="Thinking:", bg="#f0f0f0", anchor="w",
                 font=("Helvetica", 10, "bold")).grid(
            row=1, column=0, sticky="sw", padx=8, pady=(8, 2))
        self.think_text = tk.Text(self.root, wrap="word", state="disabled",
                                   bg="#f4f4f6", fg="#666666",
                                   relief="flat", bd=0, padx=8, pady=6)
        self.think_text.grid(row=1, column=0, sticky="nsew", padx=8)

        # Response panel
        tk.Label(self.root, text="Response:", bg="#f0f0f0", anchor="w",
                 font=("Helvetica", 10, "bold")).grid(
            row=2, column=0, sticky="sw", padx=8, pady=(8, 2))
        self.resp_text = tk.Text(self.root, wrap="word", state="disabled",
                                  bg="#ffffff", relief="flat", bd=0,
                                  padx=8, pady=6)
        self.resp_text.grid(row=2, column=0, sticky="nsew", padx=8)

        # Prompt input
        input_frame = tk.Frame(self.root, bg="#f0f0f0")
        input_frame.grid(row=3, column=0, sticky="ew", padx=8, pady=8)
        input_frame.columnconfigure(0, weight=1)
        self.prompt_text = tk.Text(input_frame, height=3, wrap="word",
                                    relief="solid", bd=1, padx=6, pady=6)
        self.prompt_text.grid(row=0, column=0, sticky="ew")
        self.prompt_text.bind("<Return>",       self._on_enter)
        self.prompt_text.bind("<Shift-Return>", self._on_newline)

        # Buttons
        btn_frame = tk.Frame(self.root, bg="#f0f0f0")
        btn_frame.grid(row=4, column=0, sticky="ew", padx=8)
        self.stop_btn = tk.Button(btn_frame, text="⏹ Stop",
                                   command=self._stop, state="disabled")
        self.stop_btn.pack(side="left")
        self.send_btn = tk.Button(btn_frame, text="Send", command=self.submit)
        self.send_btn.pack(side="right")

        # Status
        self.status_var = tk.StringVar(value="")
        tk.Label(self.root, textvariable=self.status_var, bg="#f0f0f0",
                 fg="#888888", anchor="w").grid(
            row=5, column=0, sticky="ew", padx=8, pady=4)

    def _load_models(self):
        def fetch():
            try:
                r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
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

    # ── Input handling ────────────────────────────────────────────────────────

    def _on_enter(self, _event):
        self.submit()
        return "break"

    def _on_newline(self, _event):
        self.prompt_text.insert(tk.INSERT, "\n")
        return "break"

    def submit(self):
        prompt = self.prompt_text.get("1.0", tk.END).strip()
        if not prompt:
            return
        self.prompt_text.delete("1.0", tk.END)
        self._set_text(self.think_text, "")
        self._set_text(self.resp_text, "")
        self._stop_flag.clear()
        self.send_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_var.set("Generating…")
        threading.Thread(target=self._stream, args=(prompt,), daemon=True).start()

    def _stop(self):
        self._stop_flag.set()

    # ── Text helpers ──────────────────────────────────────────────────────────

    def _set_text(self, widget: tk.Text, text: str):
        widget.config(state="normal")
        widget.delete("1.0", tk.END)
        if text:
            widget.insert("1.0", text)
        widget.config(state="disabled")

    # ── Streaming ─────────────────────────────────────────────────────────────

    def _stream(self, prompt: str):
        think_buf = ""
        resp_buf  = ""
        in_think  = False
        try:
            payload = {
                "model":  self.model_var.get(),
                "prompt": prompt,
                "stream": True,
                "think":  True,
            }
            with requests.post(f"{OLLAMA_URL}/api/generate",
                               json=payload, stream=True, timeout=120) as resp:
                resp.raise_for_status()
                for raw in resp.iter_lines():
                    if self._stop_flag.is_set():
                        break
                    if not raw:
                        continue
                    chunk = json.loads(raw)
                    thinking = chunk.get("thinking", "")
                    text     = chunk.get("response", "")
                    if thinking:
                        think_buf += thinking
                        self.root.after(0, lambda t=think_buf:
                            self._set_text(self.think_text, t))
                    if text:
                        combined = text
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
                                    self._set_text(self.think_text, t))
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
                                    self._set_text(self.resp_text, t))
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
            self.root.after(0, self._done)

    def _done(self):
        self.send_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_var.set("Done" if not self._stop_flag.is_set() else "Stopped")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app = OllamaGUI(root)
    root.mainloop()
