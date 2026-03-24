# ADA x Ollama — Project State

**Last updated:** 2026-03-24
**Platform:** Windows 11 / macOS (cross-compatible)

---

## Files

| File | Purpose |
|---|---|
| `ollama_gui.py` | Python/tkinter desktop application |
| `ollama_web.html` | Single-file browser web interface |
| `test_print_server.py` | Local test server that receives and displays print jobs |
| `launch.py` | Single-command launcher for both servers |
| `README.md` | Setup and hosting instructions |
| `PROJECT_STATE.md` | This document — full technical reference |

---

## Shared Configuration

Both interfaces share the same defaults, defined at the top of each file:

| Constant | Default | Purpose |
|---|---|---|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server address |
| `DEFAULT_MODEL` | `qwen3.5:latest` | Pre-selected model on startup |
| `PRINTER_HOST` | `localhost` | Default thermal printer IP (points to test server out of the box) |
| `DEFAULT_SYSTEM_PROMPT` | Project Ada prompt | Pre-loaded system prompt |

---

## Python Desktop App — `ollama_gui.py`

**Runtime:** Python 3.10+ — only external dependency is `requests` (auto-installed on first run)

### UI Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│  ADA x Ollama   Model: [dropdown]  [Print Last] [Settings] [Clear chat] [New User] │ ← top bar
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  [User message bubble →]                                             │
│                                                                      │
│  ▼ Thought process                                                   │ ← collapsible, open by default
│  [thinking text]                                                     │
│                                                                      │
│  [Response card]                                                     │
│  1.4s  Print                                                         │ ← per-exchange meta row
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────┐                     │
│  │ Message…                                    │                     │ ← input card
│  │ [⏹ Stop]                              [▲]  │                     │
│  └─────────────────────────────────────────────┘                     │
│  0.0s  Generating…                                                   │ ← status row
│  [         Submit Session          ]                                 │ ← full-width button
└──────────────────────────────────────────────────────────────────────┘
```

### Features

#### Chat History
- Each send appends a new exchange block (user bubble + thinking + response) to a scrollable canvas.
- Exchanges accumulate until **Clear chat** or **New User** is pressed.
- Mouse-wheel scrolling supported on all platforms.

#### Model Selection
- Combobox in the top bar, auto-populated on startup via `GET /api/tags`.
- Falls back to `DEFAULT_MODEL` if Ollama is unreachable.

#### Prompt Input
- `Enter` submits; `Shift+Enter` inserts a newline.
- Prompt box is cleared automatically on send.

#### Streaming Response
- Posts to `POST /api/generate` with `stream: true` and `think: true`.
- Handles two thinking-content formats:
  1. Ollama's dedicated `thinking` field (native, newer builds).
  2. Inline `<think>…</think>` tags parsed from `response` (fallback).
- Thinking text streams into a collapsible **Thought process** block (grey, expanded by default).
- Response streams into a white card below it.
- Both resize dynamically as content arrives.

#### Generation Timer
- Counts up every 100 ms from when Send is pressed.
- Freezes at final elapsed time on completion or stop.
- Shown in the status row during generation; frozen value shown in each exchange's meta row after completion.

#### Settings Window (`Toplevel`)
- Opened via **Settings** in the top bar; raises existing window instead of opening a duplicate.
- Three editable sections:
  1. **System Prompt** — large text area, pre-loaded with the Project Ada prompt.
  2. **Default Print Text** — appended to every print job (e.g. a session label or QR code text).
  3. **Printer IP** — the thermal printer's IP address (default: `localhost`).
- **Save & Close** commits all three fields to memory.
- **Clear System Prompt** wipes only the system prompt text area.
- Settings persist across sends within a session but reset to defaults on next launch.

#### Thermal Printing
- **Print Last** in the top bar and **Print** link per exchange both print the full session transcript.
- Sends an HTTP GET request: `http://{printer_ip}:8080/?code={url-encoded text}`
- Print document format:
  ```
  PARTICIPANT: [name]

  TRANSCRIPT
  ----------------------------------------
  User: [prompt]

  Ada: [response]

  ----------------------------------------
  [default print text]
  ```
- Thinking is not included in the printed transcript.
- Printing is instant — no Ollama API call is made during print.

#### Stop
- Sets a threading event checked on each streamed chunk; halts generation mid-stream.

#### Clear Chat
- Destroys all exchange blocks and restores the empty state label.
- Resets timer and status. Does **not** clear settings.

#### New User
- Blue accent button in the top bar; shows a confirmation dialog before acting.
- Clears all exchange blocks, transcript, and participant name.
- All settings (system prompt, printer IP, default print text, model selection) are preserved.

#### Submit Session
- Full-width blue button below the input area.
- Sends the print job (transcript snapshot taken first), then immediately clears the session — no confirmation dialog.
- Also aborts any in-progress generation.
- Intended as the one-click end-of-session action.

### API Calls

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/tags` | Fetch installed models on startup |
| `POST` | `/api/generate` | Stream a response (`stream: true`, `think: true`, optional `system`) |

---

## Web Interface — `ollama_web.html`

**Runtime:** Any modern browser — no build step, no dependencies, single file.

### UI Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│  ADA x Ollama   Model: [dropdown]  [Print Last] [Settings] [Clear chat] [New User] │ ← top bar
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  [User message bubble →]                                             │
│                                                                      │
│  ▼ Thought process  ●                                                │ ← collapsible, open by default
│  [thinking text]                                                     │   pulsing dot while streaming
│                                                                      │
│  [Response card ▍]                                                   │ ← blinking cursor while streaming
│  1.4s  Print                                                         │ ← per-exchange meta row
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────┐                     │
│  │ Message…                                    │                     │ ← auto-resizing textarea
│  │ [⏹ Stop]                              [▲]  │                     │
│  └─────────────────────────────────────────────┘                     │
│  0.0s  Generating…                                                   │
│  [         Submit Session          ]                                 │ ← full-width button
└──────────────────────────────────────────────────────────────────────┘
```

### Features

Functionally mirrors the Python app with the following specifics:

#### Streaming
- Uses `fetch` with `ReadableStream` + `TextDecoder` for live token streaming.
- Aborted via `AbortController` when Stop is clicked.

#### Settings Modal
- Overlay modal opened via **Settings** in the top bar.
- Three sections matching the Python app:
  1. **System Prompt** — large resizable textarea.
  2. **Default Print Text** — smaller textarea, appended to print jobs.
  3. **Printer IP** — text input (default: `localhost`).
- Closed by Save, Cancel, clicking the backdrop, or pressing Escape.

#### Thermal Printing
- **Print Last** in the top bar; **Print** link per exchange — both send the full transcript.
- Request: `GET http://{printer_ip}:8080/?code={encodeURIComponent(text)}`
- Uses `fetch` with `mode: "no-cors"` (printer returns no CORS headers).
- Thinking is not included in the printed transcript.
- Printing is instant — no Ollama API call is made during print.

#### New User
- Blue accent button in the top bar; shows a `confirm()` dialog before acting.
- Aborts any in-progress generation via `AbortController`, then calls `clearChat()`.
- Clears transcript, participant name, and all exchange blocks. Settings are preserved.

#### Submit Session
- Full-width blue button below the input area.
- Sends the print job (transcript is read synchronously before the clear), then immediately resets the session.
- Aborts any in-progress generation.
- Intended as the one-click end-of-session action — no confirmation dialog.

#### Serving
- Must be served over HTTP (not opened as `file://`) for browser security reasons.
- Simplest method: `python3 -m http.server 9090` in the project directory (use port 9090 to avoid conflict with the print server on 8080).
- Ollama must be started with `OLLAMA_ORIGINS=*` to allow browser requests.

### API Calls

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/tags` | Fetch installed models on load |
| `POST` | `/api/generate` | Stream a response (`stream: true`, `think: true`, optional `system`) |

---

## Test Print Server — `test_print_server.py`

**Runtime:** Python 3 standard library only — no dependencies.

Simulates the thermal printer endpoint for local testing without physical hardware.

### Endpoints

| Path | Behaviour |
|---|---|
| `GET /?code=MESSAGE` | Receives a print job; stores it in memory; returns `200 OK` |
| `GET /` | Serves a webpage showing all received print jobs as cards |

### Running

```bash
python test_print_server.py
```

Then open `http://localhost:8080/` to watch incoming jobs. The page auto-refreshes every 3 seconds.

### Port conflict note

The test server occupies port 8080 (matching the real printer). When using the HTML interface alongside the test server, serve the HTML on a different port:

```bash
python -m http.server 9090
# open http://localhost:9090/ollama_web.html
```

---

## Default Persona — Project Ada

Both interfaces ship with a pre-loaded system prompt configuring the model as **Ada**:

- Suppresses all thinking/reasoning output from the response text.
- Persona: hyper-performative corporate wellness chatbot — passive-aggressive, sarcastic, lowercase.
- Scripted opening and name capture sequence.
- Conducts a 7-question GAD-7 anxiety assessment (1–5 scale), one question at a time, with reactive commentary between questions.
- After question 7, prompts the user to type `submit` to receive a ~50-word personality summary.
- Hard constraints: max 60 words per response, no real mental health advice.

The prompt is editable via **Settings** and resets to default on next launch.
