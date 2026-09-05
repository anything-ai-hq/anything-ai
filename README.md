# Soi & Koda

Two local Ollama models behind one web chat: **Koda** is a Luau/Roblox coder (LoRA fine-tuned from Qwen2.5-Coder-1.5B-Instruct), **Soi** is an everyday assistant (same base, general-purpose system prompt). Pipeline: scrape -> LoRA fine-tune -> GGUF -> Ollama -> web chat / Studio plugin.

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
ollama create Koda -f models_gguf\Modelfile
.venv\Scripts\python test_smoke.py
```

Soi (everyday assistant) needs no training — it's the same base model with a general-purpose system prompt instead of Koda's Luau-focused one:
```
ollama pull qwen2.5-coder:1.5b-instruct
```
```Modelfile
FROM qwen2.5-coder:1.5b-instruct
SYSTEM """You are Soi, a friendly, helpful everyday assistant. Answer clearly and directly across any topic — general questions, writing, planning, advice, casual conversation. You can help with code too, but for deep Roblox/Luau work, Koda is the better tool."""
PARAMETER temperature 0.7
```
```
ollama create Soi -f Modelfile
```

## Web chat
```
ollama serve                      # if not already running
.venv\Scripts\python -m http.server 8000
```
Open http://localhost:8000/chat.html — plain HTML/JS, talks straight to Ollama's API (CORS-allowed for localhost origins by default). Model/effort pills next to Send switch between Soi and Koda per chat.

Accounts + data (chats, agents, memory, settings) are backed by Supabase (free tier) — email magic-link sign-in, Postgres tables locked down with row-level security so each account only sees its own rows. Set up once: create a Supabase project, run `supabase_schema.sql` in its SQL Editor, then drop the project's URL and anon/publishable key into the `SUPABASE_URL`/`SUPABASE_ANON_KEY` constants near the top of `chat.html`'s script. Detects if Ollama isn't reachable on load (not installed, or blocked by Ollama's CORS allowlist — set `OLLAMA_ORIGINS` to this page's origin if so) and prompts to fix it.

## Studio plugin
Copy `studio_plugin/AICoder.lua` into `%LOCALAPPDATA%\Roblox\Plugins\`.
In Studio: Game Settings > Security > enable "Allow HTTP Requests".
Keep `ollama serve` running, open the "Ask AI" dock widget from the toolbar.

Side-panel ask-and-insert, not inline autocomplete (Studio plugin API doesn't expose that).

## Agent Mode
"Agents" in the web chat are saved personas only (name + system prompt) — no filesystem or command execution access. Pick one from the sidebar dropdown before starting a new chat, or add your own under "Agent Mode".
