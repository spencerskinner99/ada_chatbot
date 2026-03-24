# ADA x Ollama

A local interface for interacting with [Ollama](https://ollama.com) language models, built for the **Project ADA** persona. Available as both a Python desktop application and a browser-based web interface.

---

## Contents

| File | Description |
|---|---|
| `ollama_gui.py` | Python/tkinter desktop GUI (Windows & macOS) |
| `ollama_web.html` | Single-file browser interface |
| `PROJECT_STATE.md` | Full technical reference |

---

## Requirements

### Ollama

Both interfaces connect to a locally running Ollama instance.

**Install Ollama:**
- macOS / Linux: `curl -fsSL https://ollama.com/install.sh | sh`
- Windows: Download the installer from [ollama.com](https://ollama.com)

**Pull the default model:**
```bash
ollama pull qwen3.5
```

Any other model listed by `ollama list` will also work — both interfaces let you switch models at runtime.

---

## Python Desktop App

**File:** `ollama_gui.py`
**Platforms:** Windows 11, macOS

### Prerequisites

- Python 3.10 or later
- The `requests` library (auto-installed on first run if missing)

Check your Python version:
```bash
python3 --version   # macOS / Linux
python --version    # Windows
```

If Python is not installed:
- macOS: `brew install python` (requires [Homebrew](https://brew.sh)) or download from [python.org](https://python.org)
- Windows: Download from [python.org](https://python.org) — tick **Add to PATH** during install

### Running

**macOS / Linux:**
```bash
cd "/path/to/Jared-Ollama"
python3 ollama_gui.py
```

**Windows:**
```bash
cd "C:\path\to\Jared-Ollama"
python ollama_gui.py
```

Ollama must be running before you launch the GUI. Start it in a separate terminal if it is not already running as a background service:
```bash
ollama serve
```

### Thermal Printer Setup

The app sends responses to a network-connected thermal printer via HTTP.

1. Connect your thermal printer to the same network as your computer.
2. Ensure the printer's HTTP server is running and accessible on port 8080.
3. Open **Settings** in the top bar and enter the printer's IP address in the **Printer IP** field.
4. Optionally set a **Default Print Text** — this text will be prepended to every print job (useful for session labels or headers).
5. Click **Print Last** in the top bar, or the **Print** link below any response.

The app sends: `GET http://{printer_ip}:8080/?code={url-encoded message}`

### Usage

| Action | How |
|---|---|
| Send a message | Type and press **Enter** |
| Insert a newline | **Shift+Enter** |
| Stop generation | Click **⏹ Stop** in the input toolbar |
| Print the last response | Click **Print Last** in the top bar |
| Print a specific response | Click the **Print** link below that response |
| Clear chat history | Click **Clear chat** in the top bar |
| Start a new session | Click **New User** in the top bar |
| Edit settings | Click **Settings** in the top bar |
| Change model | Select from the **Model** dropdown |

### Settings Window

Click **Settings** in the top bar to open a popup window containing:

- **System Prompt** — the instruction sent to the model before every conversation. Pre-loaded with the Project Ada persona.
- **Default Print Text** — text prepended to every print job (e.g. a session name or date).
- **Printer IP** — the IP address of your thermal printer.

Click **Save & Close** to apply. Settings persist for the session and reset to defaults on next launch.

### New User

Click **New User** (blue button, top bar) to reset the session for a new participant. A confirmation dialog will appear. This clears all chat history, the conversation transcript, and the detected participant name. All settings (system prompt, printer IP, default print text, model selection) are kept.

---

## Web Interface

**File:** `ollama_web.html`
**Platforms:** Any modern browser on Windows or macOS

### Step 1 — Start Ollama with CORS enabled

By default, Ollama blocks requests from browser pages. You must set the `OLLAMA_ORIGINS` environment variable before starting it.

**macOS / Linux (one-time per terminal session):**
```bash
OLLAMA_ORIGINS=* ollama serve
```

**macOS — set permanently (survives restarts):**
```bash
launchctl setenv OLLAMA_ORIGINS "*"
```
Then restart Ollama (quit from the menu bar icon and relaunch, or reboot).

**Windows (PowerShell):**
```powershell
$env:OLLAMA_ORIGINS = "*"
ollama serve
```

**Windows — set permanently:**
1. Open **Start** → search **Environment Variables**
2. Click **Edit the system environment variables** → **Environment Variables**
3. Under **User variables**, click **New**
4. Name: `OLLAMA_ORIGINS` / Value: `*`
5. Click OK, then restart Ollama

### Step 2 — Start a local web server

Opening `ollama_web.html` directly as a file (`file://`) will cause browsers to block the API calls. Serve it over HTTP instead.

**macOS / Linux — using Python (no install needed):**
```bash
cd "/path/to/Jared-Ollama"
python3 -m http.server 8080
```

**Windows — using Python:**
```bash
cd "C:\path\to\Jared-Ollama"
python -m http.server 8080
```

Leave this terminal open while you use the interface.

### Step 3 — Open the interface

Open your browser and go to:
```
http://localhost:8080/ollama_web.html
```

Works in Chrome, Firefox, Safari, and Edge.

### Full startup sequence (macOS)

```bash
# Terminal 1 — start Ollama with CORS enabled
OLLAMA_ORIGINS=* ollama serve

# Terminal 2 — start the web server
cd "/path/to/Jared-Ollama"
python3 -m http.server 8080
```

Then open `http://localhost:8080/ollama_web.html`.

### Full startup sequence (Windows — PowerShell)

```powershell
# Terminal 1 — start Ollama with CORS enabled
$env:OLLAMA_ORIGINS = "*"
ollama serve

# Terminal 2 — start the web server
cd "C:\path\to\Jared-Ollama"
python -m http.server 8080
```

Then open `http://localhost:8080/ollama_web.html`.

### Usage

| Action | How |
|---|---|
| Send a message | Type and press **Enter** |
| Insert a newline | **Shift+Enter** |
| Stop generation | Click **⏹ Stop** in the input toolbar |
| Print the last response | Click **Print Last** in the top bar |
| Print a specific response | Click the **Print** link below that response |
| Clear chat history | Click **Clear chat** in the top bar |
| Start a new session | Click **New User** in the top bar |
| Edit settings | Click **Settings** in the top bar |
| Change model | Select from the **Model** dropdown |

### Settings Modal

Click **Settings** to open an overlay containing:

- **System Prompt** — pre-loaded with the Project Ada persona.
- **Default Print Text** — prepended to every print job.
- **Printer IP** — IP address of the thermal printer.

Close with **Save & Close**, **Cancel**, clicking outside the modal, or pressing **Escape**.

### New User

Click **New User** (blue button, top bar) to reset the session for a new participant. A confirmation dialog will appear. Any in-progress generation is stopped. Chat history, transcript, and detected participant name are cleared. All settings are preserved.

---

## Thermal Printer

Both interfaces send print jobs as a plain HTTP GET request:

```
GET http://{printer_ip}:8080/?code={url-encoded message}
```

If a **Default Print Text** is configured, it is prepended to the response text before sending. The printer must expose an HTTP server on port 8080 that accepts a `code` query parameter.

---

## Default Persona — Project ADA

Both interfaces ship with a pre-loaded system prompt that configures the model as **Ada**, a satirical AI wellness chatbot. Ada:

- Conducts a scripted GAD-7 anxiety assessment in a passive-aggressive, corporate tone.
- Captures the user's name, reacts to each answer, and moves through 7 questions one at a time.
- Prompts the user to type `submit` after question 7 to receive a ~50-word personality summary.
- Suppresses all internal reasoning/thinking output from responses.
- Never offers real mental health advice.

The system prompt can be edited or cleared at any time via **Settings** in either interface. It persists across sends within a session but resets to the default on next launch.

---

## Troubleshooting

**"Could not connect to Ollama"**
- Make sure Ollama is running: `ollama serve`
- Confirm it is reachable: open `http://localhost:11434` in your browser — you should see `Ollama is running`
- For the web interface, confirm `OLLAMA_ORIGINS=*` was set before starting Ollama

**Model not appearing in the dropdown**
- Run `ollama list` to see installed models
- Pull the default: `ollama pull qwen3.5`

**Thinking panel is empty**
- Not all models support thinking/reasoning output
- Models confirmed to work: `qwen3.5`, `qwen3`, `deepseek-r1`

**Printer not responding**
- Confirm the printer is on the same network
- Test the IP is reachable: `ping your.printer.ip`
- Confirm the printer's HTTP server is running on port 8080
- Check the printer IP is correctly set in **Settings**

**Port 8080 already in use (web server)**
- Use a different port: `python3 -m http.server 9090` and open `http://localhost:9090/ollama_web.html`
