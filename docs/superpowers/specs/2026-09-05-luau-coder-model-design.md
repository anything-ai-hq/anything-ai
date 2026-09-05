# Luau/Roblox local coding model

## Goal
Cheap, small, locally-hosted LLM fine-tuned to write Luau/Roblox code, usable from inside Roblox Studio via a plugin.

## Hardware
RTX 5050 (consumer GPU, already used for `my-ai` project). Budget: 1.5B param base model, 4-bit.

## Components

### 1. Dataset builder (`scrape_dataset.py`)
- Query GitHub code search for `.lua` / `.luau` files in Roblox-related repos.
- Shallow-clone permissively-licensed repos only (MIT/Apache/BSD; skip unlicensed).
- Walk cloned repos, collect `.lua`/`.luau` files, strip huge/vendored/minified files.
- Dedupe by content hash.
- Convert into instruct pairs: leading comment/docstring or function signature -> prompt, function body -> completion. Fallback generic prompt ("complete this Luau script:") when no comment present.
- Output: `data/luau_corpus.jsonl` (`{"prompt": ..., "completion": ...}` per line).
- Self-check: script asserts collected example count > 0 before writing, prints final count.

### 2. LoRA fine-tune (`train_lora.py`)
- Base model: `unsloth/Qwen2.5-Coder-1.5B-Instruct`, loaded 4-bit via `unsloth`.
- LoRA config: r=16, standard attention+mlp target modules.
- Train via `SFTTrainer` on `luau_corpus.jsonl`, 1-3 epochs (epoch count chosen from dataset size at run time).
- Save adapter to `adapters/luau-lora/`.

### 3. Export (`export_gguf.py`)
- Merge LoRA into base weights.
- Export merged model to GGUF, quantized `q4_k_m`, via unsloth's built-in GGUF export.
- Output: `models/luau-coder.gguf`.

### 4. Serving
- `Modelfile` (`FROM ./models/luau-coder.gguf`, minimal system prompt: "You are a Luau/Roblox coding assistant.").
- `ollama create luau-coder -f Modelfile`.
- Served at `http://localhost:11434`.

### 5. Roblox Studio plugin (`studio_plugin/AICoder.lua`)
- DockWidgetPluginGui with a prompt textbox + "Ask" button + response textbox.
- On submit: `HttpService:RequestAsync` (POST) to `http://localhost:11434/api/generate` with the prompt (optionally prefixed with currently selected script text, if accessible).
- Displays response in the panel; a "Insert" button pastes it into the currently open script via `ScriptEditorService`.
- **Not** inline/ghost-text autocomplete — Studio's plugin API doesn't expose keystroke-level completion. This is an ask-and-insert side panel, confirmed acceptable with user.
- Requires enabling "Allow HTTP Requests" in Studio's Game Settings for local testing (`localhost` requests must be permitted).

## Testing
- Dataset script: self-asserts non-empty corpus.
- Training: smoke test script that loads `luau-coder` via Ollama API, sends a fixed prompt (e.g. "write a function that returns the sum of a table of numbers in Luau"), asserts response is non-empty and contains `function`/`end`.
- Plugin: manual check in Studio — open panel, submit prompt, confirm response appears and Insert writes into script editor.

## Out of scope
- Full (non-LoRA) fine-tuning.
- Inline/ghost-text autocomplete.
- Any cloud training/serving — everything runs locally on the RTX 5050 box.
