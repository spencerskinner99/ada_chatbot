# ADA x Ollama — Project State

**Last updated:** 2026-03-24 (New User button added)
**Platform:** Windows 11 / macOS (cross-compatible)

---

## Files

| File | Purpose |
|---|---|
| `ollama_gui.py` | Python/tkinter desktop application |
| `ollama_web.html` | Single-file browser web interface |
| `README.md` | Setup and hosting instructions |
| `PROJECT_STATE.md` | This document — full technical reference |

---

## Shared Configuration

Both interfaces share the same defaults, defined at the top of each file:

| Constant | Default | Purpose |
|---|---|---|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server address |
| `DEFAULT_MODEL` | `qwen3.5:latest` | Pre-selected model on startup |
| `PRINTER_HOST` | `192.168.1.100` | Default thermal printer IP |
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
└──────────────────────────────────────────────────────────────────────┘
```

### Features

#### Chat History
- Each send appends a new exchange block (user bubble + thinking + response) to a scrollable canvas.
- Exchanges accumulate until **Clear chat** is pressed.
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
  2. **Default Print Text** — prepended to every print job (e.g. a session header).
  3. **Printer IP** — the thermal printer's IP address.
- **Save & Close** commits all three fields to memory.
- **Clear System Prompt** wipes only the system prompt text area.
- Settings persist across sends within a session but reset to defaults on next launch.

#### Thermal Printing
- **Print Last** in the top bar prints the most recent response.
- **Print** link in each exchange's meta row prints that specific response.
- Sends an HTTP GET request: `http://{printer_ip}:8080/?code={url-encoded text}`
- If a Default Print Text prefix is set, it is prepended to the message before sending.
- Success/error reported in the status label.

#### Stop
- Sets a threading event checked on each streamed chunk; halts generation mid-stream.

#### Clear Chat
- Destroys all exchange blocks and restores the empty state label.
- Resets timer and status. Does **not** clear the system prompt or print settings.

#### New User
- Blue accent button in the top bar; shows a confirmation dialog before acting.
- Calls `_clear_chat` internally — clears all exchange blocks, transcript, participant name, timer, and status.
- All settings (system prompt, printer IP, default print text, model selection) are preserved.

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
  2. **Default Print Text** — smaller textarea, prepended to print jobs.
  3. **Printer IP** — text input.
- Closed by Save, Cancel, clicking the backdrop, or pressing Escape.

#### Thermal Printing
- **Print Last** in the top bar; **Print** link per exchange — both send:
  `GET http://{printer_ip}:8080/?code={encodeURIComponent(text)}`
- Uses `fetch` with `mode: "no-cors"` (printer returns no CORS headers).
- Default Print Text prefix is prepended if set.

#### New User
- Blue accent button in the top bar; shows a `confirm()` dialog before acting.
- Aborts any in-progress generation via `AbortController`, then calls `clearChat()`.
- Clears transcript, participant name, and all exchange blocks. Settings are preserved.

#### Serving
- Must be served over HTTP (not opened as `file://`) for browser security reasons.
- Simplest method: `python3 -m http.server 8080` in the project directory.
- Ollama must be started with `OLLAMA_ORIGINS=*` to allow browser requests.

### API Calls

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/tags` | Fetch installed models on load |
| `POST` | `/api/generate` | Stream a response (`stream: true`, `think: true`, optional `system`) |

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
