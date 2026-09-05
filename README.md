# luau-coder

Local, cheap Luau/Roblox coding model: scrape -> LoRA fine-tune -> GGUF -> Ollama -> Studio plugin.

## Setup
```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## Run
```
set GITHUB_TOKEN=ghp_xxx          # optional, raises GitHub rate limit
.venv\Scripts\python scrape_dataset.py
.venv\Scripts\python train_lora.py
.venv\Scripts\python export_gguf.py
ollama create luau-coder -f models_gguf\Modelfile
.venv\Scripts\python test_smoke.py
```

## Web chat
```
ollama serve                      # if not already running
.venv\Scripts\python -m http.server 8000
```
Open http://localhost:8000/chat.html — plain HTML/JS, talks straight to Ollama's API (CORS-allowed for localhost origins by default). No build step, no framework.

## Studio plugin
Copy `studio_plugin/AICoder.lua` into `%LOCALAPPDATA%\Roblox\Plugins\`.
In Studio: Game Settings > Security > enable "Allow HTTP Requests".
Keep `ollama serve` running, open the "Ask AI" dock widget from the toolbar.

Side-panel ask-and-insert, not inline autocomplete (Studio plugin API doesn't expose that).

## Agent Mode
"Agents" in the web chat are saved personas only (name + system prompt) — no filesystem or command execution access. Pick one from the sidebar dropdown before starting a new chat, or add your own under "Agent Mode".
