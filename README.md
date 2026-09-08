# Anything.ai

Three local models behind one web chat: **Koda** is a Luau/Roblox coder (LoRA fine-tuned from Qwen2.5-Coder-1.5B-Instruct), **Soi** is an everyday assistant (same base, general-purpose system prompt), both served via Ollama. **Vela** is local image generation (SD-Turbo via `diffusers`, served by `vela_server.py`) — a real model in the chat's model dropdown for subscribed/admin/granted accounts (everyone else gets a one-shot "meet Vela" popup demo). Pipeline: scrape -> LoRA fine-tune -> GGUF -> Ollama -> web chat / Studio plugin.

Soi can also run entirely off a free cloud API key instead of local Ollama (Settings → "Run Soi in the cloud") — see [§ Soi cloud fallback](#soi-cloud-fallback-no-ollama-needed). Koda and Vela can't do this; they're custom weights no free-tier API hosts.

## Setup
```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## New PC setup
`git clone` alone is **not enough to run Koda/Soi** — their gguf weights are gitignored and don't transport with the repo. Both are published as a single GitHub Release, fully self-contained (Soi's release copy is the already-merged weights, not a Modelfile layered on a separate base pull — nothing else to fetch):

```
curl -L -o Koda.gguf https://github.com/anything-ai-hq/anything-ai/releases/download/models-v1/Koda.gguf
curl -L -o Koda.Modelfile https://github.com/anything-ai-hq/anything-ai/releases/download/models-v1/Koda.Modelfile
ollama create Koda -f Koda.Modelfile

curl -L -o Soi.gguf https://github.com/anything-ai-hq/anything-ai/releases/download/models-v1/Soi.gguf
curl -L -o Soi.Modelfile https://github.com/anything-ai-hq/anything-ai/releases/download/models-v1/Soi.Modelfile
ollama create Soi -f Soi.Modelfile

ollama pull moondream    # vision model, public, silently required for screenshot/video attach
```

Run from any folder — each Modelfile references its gguf by relative filename, so just keep the pairs together while running `ollama create`. Full release page: https://github.com/anything-ai-hq/anything-ai/releases/tag/models-v1

Retraining from scratch instead (only needed if you're changing the training data/method, not for a plain new-PC setup) is still possible via the scrape+train+export pipeline below (30-60 min depending on GPU). After retraining, push a new release: `gh release create models-v2 Koda.gguf Koda.Modelfile Soi.gguf Soi.Modelfile --repo anything-ai-hq/anything-ai --title "..."` and update the `models-v1` URLs here and in `chat.html`'s `MODEL_FIX.koda`.

The app's own "Checking for Ollama..." popup on load checks for all three (`Koda`, `Soi`, `moondream`) and tells you exactly which are missing and how to fix each — use it to verify a new setup instead of guessing.

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

Accounts + data (chats, agents, memory, settings) are backed by Supabase (free tier) — email magic-link sign-in, Postgres tables locked down with row-level security so each account only sees its own rows. Set up once: create a Supabase project, run **both** `supabase_schema.sql` and `supabase_permissions.sql` in its SQL Editor (the second one creates `profiles`/`permissions` and the Vela quota/admin-panel functions — skip it and Vela access checks and admin.html break with "relation does not exist" errors), then drop the project's URL and anon/publishable key into the `SUPABASE_URL`/`SUPABASE_ANON_KEY` constants near the top of `chat.html`'s script. Detects if Ollama isn't reachable on load (not installed, or blocked by Ollama's CORS allowlist — set `OLLAMA_ORIGINS` to this page's origin if so) and prompts to fix it.

## Live site

Hosted free on GitHub Pages: **https://anything-ai-hq.github.io/anything-ai/**

To publish an update:
```
git add -A
git commit -m "..."
git push github-pages master
```
Pages rebuilds automatically in under a minute, no separate deploy command needed. (We started on Netlify but its team account hit an undocumented billing block on new deploys — GitHub Pages has no such credit system and just works off a plain push.)

Any browser hitting this page needs its own local Ollama, with `OLLAMA_ORIGINS` including `https://anything-ai-hq.github.io` (see the in-app "Instructions" page for the exact fix).

## Vision (screenshots + video frames)
```
ollama pull moondream
```
Koda/Soi are text-only (Qwen2.5-Coder has no vision tower), so attaching a screenshot or video (📎 button in the input row) routes to `moondream` instead - a separate small (1.8B) vision model, not a capability of the chat models themselves. Video "understanding" samples 4 frames client-side (HTML5 `<video>` + `<canvas>`, no server-side ffmpeg) and describes them as a set of images - a summary of sampled frames, not continuous video understanding, which nothing at this scale actually does locally. Vision replies don't carry prior chat history (moondream has no context of a Koda/Soi conversation) and raw image bytes aren't persisted to Supabase (would bloat every row) - only a text label survives after the turn.

## Vela (image generation)
```
.venv\Scripts\python vela_server.py
```
Serves on `http://localhost:7860`, first run downloads SD-Turbo (~5-6GB). Accounts with access (dev / subscribed / granted `vela` in the admin editor) get Vela as a real model in the chat dropdown — quota-checked server-side via the `use_image_generation` Postgres function (20/day, unlimited for dev). Everyone else gets a one-shot generation demo in the "Meet Vela" popup instead. Same CORS-from-any-origin approach as Ollama, so it works from the deployed site too, as long as `vela_server.py` is running on your machine. No Ollama involvement; Ollama doesn't serve image models.

Generated images are **not persisted to Supabase** — only a text placeholder ("🎨 [Vela image — not saved, refresh loses it]") survives a reload, matching the vision-attachment decision (base64 image bytes would bloat every chat row). The image itself is visible for the current session only.

## Soi cloud fallback (no Ollama needed)
Settings → "Run Soi in the cloud" lets anyone use Soi with zero local setup — no Ollama, no GPU, nothing to install. Paste a free key from [openrouter.ai/keys](https://openrouter.ai/keys) and a model id (default: whatever's currently free on OpenRouter — check `https://openrouter.ai/api/v1/models` and filter for `id` ending in `:free`, since the free lineup rotates and a hardcoded default will eventually go stale). The key is sent straight from the browser to OpenRouter and stored only in the user's own Supabase settings row — same trust model as the existing BYOK custom-model feature, just not gated behind a subscription since the whole point is removing the local-hardware requirement for everyone.

Koda and Vela can't do this — they're custom fine-tuned/trained weights that no free-tier API hosts. Only Soi (public base model + a system prompt, nothing custom) is eligible.

One rough edge: the "Checking for Ollama..." popup on load still checks for local `Soi`/`Koda`/`moondream` regardless of a configured cloud key, so a cloud-only Soi user will still see it flag Soi/Koda/moondream as missing. Not a functional blocker ("Continue anyway" dismisses it and cloud Soi works fine) — just not aware of the cloud fallback yet.

## Studio plugin
Copy `studio_plugin/AICoder.lua` into `%LOCALAPPDATA%\Roblox\Plugins\`.
In Studio: Game Settings > Security > enable "Allow HTTP Requests".
Keep `ollama serve` running, open the "Ask AI" dock widget from the toolbar.

Side-panel ask-and-insert, not inline autocomplete (Studio plugin API doesn't expose that).

## Agent Mode
"Agents" in the web chat are saved personas only (name + system prompt) — no filesystem or command execution access. Pick one from the sidebar dropdown before starting a new chat, or add your own under "Agent Mode".
