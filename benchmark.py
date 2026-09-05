"""Compare luau-coder against the untuned base model on Roblox/Luau tasks.

No public Luau benchmark exists, so this is a small handwritten task set with
cheap automatic scoring (syntax-balance heuristic + expected-API keyword
hits) — a proxy for quality, not a rigorous eval. Read the saved outputs in
benchmark_results.json yourself for the real signal.

Usage: python benchmark.py
Requires: ollama serve running, and the base model pulled:
    ollama pull qwen2.5-coder:1.5b-instruct
"""
import json
import re
import urllib.request

BASE_MODEL = "qwen2.5-coder:1.5b-instruct"  # untuned, same size as Koda
TUNED_MODEL = "Koda"

TASKS = [
    ("Write a Luau function that returns the sum of a table of numbers.", ["function", "end"]),
    ("Write a Luau script that fires a RemoteEvent named 'Damage' from a LocalScript to the server, passing an amount parameter.", ["RemoteEvent", "FireServer"]),
    ("Write a Luau ModuleScript that implements a simple class with a constructor and a method, using metatables.", ["setmetatable", "__index"]),
    ("Write a Luau function that debounces rapid calls, only allowing one call per second.", ["wait", "clock", "tick"]),
    ("Write Luau server script code that listens for a RemoteEvent 'Damage' via OnServerEvent and applies damage to a humanoid.", ["OnServerEvent", "Humanoid"]),
    ("Write a Luau function that performs a raycast from a part's position downward to check for ground.", ["Raycast"]),
    ("Write a Luau function that tweens a part's transparency to 1 over 2 seconds using TweenService.", ["TweenService", "TweenInfo"]),
    ("Write a Luau function that saves player data to a DataStore, with pcall error handling.", ["DataStore", "pcall"]),
    ("Write a Luau function that returns true if a table is empty.", ["function", "end"]),
    ("Write a Luau function that clones a template part and parents it to workspace.", ["Clone", "Parent"]),
    ("Write a Luau function that connects to PlayerAdded and prints the player's name.", ["PlayerAdded", "Players"]),
    ("Write a Luau function implementing a basic state machine with states 'Idle' and 'Running'.", ["function", "end"]),
    ("Write a Luau function that binds an action to a key using ContextActionService.", ["ContextActionService", "BindAction"]),
    ("Write a Luau function that creates a BindableEvent and fires it.", ["BindableEvent", "Fire"]),
    ("Write a Luau function that formats a number with comma separators, e.g. 1234567 -> '1,234,567'.", ["function", "end"]),
]


def ask(model: str, prompt: str) -> str:
    body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/generate", data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read()).get("response", "")


def extract_code(text: str) -> str:
    """Pull the first fenced code block out, if any — models often wrap code
    in prose explanation, and counting keywords in prose wrecks the balance
    heuristic below."""
    match = re.search(r"```(?:lua|luau)?\s*(.*?)```", text, re.DOTALL)
    return match.group(1) if match else text


def syntax_balance_ok(text: str) -> bool:
    """Cheap heuristic, not a real parser: keyword/bracket balance only."""
    code = extract_code(text)
    opens = len(re.findall(r"\b(function|do|if|for|while)\b", code))
    ends = len(re.findall(r"\bend\b", code))
    if opens > 0 and abs(opens - ends) > 1:
        return False
    for open_c, close_c in [("(", ")"), ("{", "}"), ("[", "]")]:
        if code.count(open_c) != code.count(close_c):
            return False
    return True


def keyword_hit_rate(code: str, keywords: list[str]) -> float:
    hits = sum(1 for kw in keywords if kw.lower() in code.lower())
    return hits / len(keywords)


def score_model(model: str) -> tuple[dict, list[dict]]:
    records = []
    for prompt, keywords in TASKS:
        response = ask(model, prompt)
        records.append({
            "prompt": prompt,
            "response": response,
            "syntax_ok": syntax_balance_ok(response),
            "keyword_hit_rate": keyword_hit_rate(response, keywords),
        })
    n = len(records)
    summary = {
        "model": model,
        "syntax_ok_rate": sum(r["syntax_ok"] for r in records) / n,
        "avg_keyword_hit_rate": sum(r["keyword_hit_rate"] for r in records) / n,
    }
    return summary, records


def main():
    results = {}
    for model in (BASE_MODEL, TUNED_MODEL):
        print(f"Running {len(TASKS)} tasks against {model}...")
        summary, records = score_model(model)
        results[model] = {"summary": summary, "records": records}
        print(f"  syntax_ok_rate={summary['syntax_ok_rate']:.2f}  avg_keyword_hit_rate={summary['avg_keyword_hit_rate']:.2f}")

    with open("benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n=== Summary ===")
    for model, data in results.items():
        s = data["summary"]
        print(f"{model:35s} syntax_ok={s['syntax_ok_rate']*100:5.1f}%   keyword_hits={s['avg_keyword_hit_rate']*100:5.1f}%")
    print("\nFull outputs saved to benchmark_results.json")


if __name__ == "__main__":
    main()
