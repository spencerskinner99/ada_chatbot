# ADA x Ollama

A local interface for interacting with [Ollama](https://ollama.com) language models, built for the **Project ADA** persona. Available as both a Python desktop application and a browser-based web interface.

---

## Contents

| File | Description |
|---|---|
| `ollama_gui.py` | Python/tkinter desktop GUI (Windows & macOS) |
| `ollama_web.html` | Single-file browser interface |
| `test_print_server.py` | Local test server for print jobs (no printer required) |
| `launch.py` | Single-command launcher for both servers |
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

### Usage

| Action | How |
|---|---|
| Send a message | Type and press **Enter** |
| Insert a newline | **Shift+Enter** |
| Stop generation | Click **⏹ Stop** in the input toolbar |
| Print the full transcript | Click **Print Last** in the top bar |
| Print from a specific exchange | Click the **Print** link below that response |
| Submit session (print + reset) | Click **Submit Session** below the input |
| Clear chat history | Click **Clear chat** in the top bar |
| Start a new session | Click **New User** in the top bar |
| Edit settings | Click **Settings** in the top bar |
| Change model | Select from the **Model** dropdown |

### Settings Window

Click **Settings** in the top bar to open a popup window containing:

- **System Prompt** — the instruction sent to the model before every conversation. Pre-loaded with the Project Ada persona.
- **Default Print Text** — text appended to every print job (e.g. a session label).
- **Printer IP** — the IP address of your thermal printer (default: `localhost` for the test server).

Click **Save & Close** to apply. Settings persist for the session and reset to defaults on next launch.

### Submit Session

Click **Submit Session** (full-width blue button below the input area) to end a session. It:

1. Sends the print job immediately (no confirmation needed).
2. Clears all chat history, transcript, and participant name.
3. Leaves all settings intact — ready for the next participant.

### New User

Click **New User** (blue button, top bar) to reset the session for a new participant. A confirmation dialog will appear. This clears all chat history, the conversation transcript, and the detected participant name. All settings are kept.

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

> **Note:** Use port **9090** (not 8080) to avoid conflict with the test print server.

**macOS / Linux:**
```bash
cd "/path/to/Jared-Ollama"
python3 -m http.server 9090
```

**Windows:**
```bash
cd "C:\path\to\Jared-Ollama"
python -m http.server 9090
```

### Step 3 — Open the interface

Open your browser and go to:
```
http://localhost:9090/ollama_web.html
```

Works in Chrome, Firefox, Safari, and Edge.

### Full startup sequence (macOS)

```bash
# Terminal 1 — start Ollama with CORS enabled
OLLAMA_ORIGINS=* ollama serve

# Terminal 2 — launch both servers in one command
cd "/path/to/Jared-Ollama"
python3 launch.py
```

Then open:
- Chat interface: `http://localhost:9090/ollama_web.html`
- Print job viewer: `http://localhost:8080/`

### Full startup sequence (Windows — PowerShell)

```powershell
# Terminal 1 — start Ollama with CORS enabled
$env:OLLAMA_ORIGINS = "*"
ollama serve

# Terminal 2 — launch both servers in one command
cd "C:\path\to\Jared-Ollama"
python launch.py
```

Then open:
- Chat interface: `http://localhost:9090/ollama_web.html`
- Print job viewer: `http://localhost:8080/`

### Usage

| Action | How |
|---|---|
| Send a message | Type and press **Enter** |
| Insert a newline | **Shift+Enter** |
| Stop generation | Click **⏹ Stop** in the input toolbar |
| Print the full transcript | Click **Print Last** in the top bar |
| Print from a specific exchange | Click the **Print** link below that response |
| Submit session (print + reset) | Click **Submit Session** below the input |
| Clear chat history | Click **Clear chat** in the top bar |
| Start a new session | Click **New User** in the top bar |
| Edit settings | Click **Settings** in the top bar |
| Change model | Select from the **Model** dropdown |

### Settings Modal

Click **Settings** to open an overlay containing:

- **System Prompt** — pre-loaded with the Project Ada persona.
- **Default Print Text** — appended to every print job.
- **Printer IP** — IP address of the thermal printer (default: `localhost`).

Close with **Save & Close**, **Cancel**, clicking outside the modal, or pressing **Escape**.

### Submit Session

Click **Submit Session** (full-width blue button below the input area) to end a session. It sends the print job, stops any in-progress generation, and resets to a clean state — no confirmation dialog.

### New User

Click **New User** (blue button, top bar) to reset the session for a new participant. A confirmation dialog will appear. Any in-progress generation is stopped. Chat history, transcript, and detected participant name are cleared. All settings are preserved.

---

## Thermal Printer

Both interfaces send print jobs as a plain HTTP GET request:

```
GET http://{printer_ip}:8080/?code={url-encoded message}
```

The printer must expose an HTTP server on port 8080 that accepts a `code` query parameter.

**Print document format:**
```
PARTICIPANT: [name]

TRANSCRIPT
----------------------------------------
User: [prompt]

Ada: [response]

----------------------------------------
[default print text]
```

Thinking/reasoning is not included in the printed output.

---

## Test Print Server

For testing without a physical printer, use the launcher (recommended) or run the server directly:

```bash
python3 launch.py        # starts both servers together (recommended)
python3 test_print_server.py   # print server only
```

This starts a server on port 8080 that:
- Accepts print jobs at `http://localhost:8080/?code=MESSAGE`
- Displays all received jobs as cards at `http://localhost:8080/`
- Auto-refreshes every 3 seconds

The default printer IP in both interfaces is already set to `localhost`, so printing works immediately without changing any settings.

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
- Run `python test_print_server.py` to test locally without hardware
- For a real printer: confirm it is on the same network, its HTTP server is running on port 8080, and the correct IP is set in **Settings**

**Port conflict (web server vs test print server)**
- Run the print server on 8080 and the web file server on a different port: `python3 -m http.server 9090`
- Open the interface at `http://localhost:9090/ollama_web.html`
