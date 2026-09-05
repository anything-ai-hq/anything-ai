"""Smoke test: ask the served Ollama model for Luau code, check it looks like Luau.

Usage: python test_smoke.py   (requires `ollama create luau-coder -f Modelfile` already run)
"""
import json
import sys
import urllib.request

PROMPT = "Write a Luau function that returns the sum of a table of numbers."


def main():
    body = json.dumps({"model": "luau-coder", "prompt": PROMPT, "stream": False}).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/generate", data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())

    text = result.get("response", "")
    assert text.strip(), "Empty response from model"
    assert "function" in text and "end" in text, f"Response doesn't look like Luau:\n{text}"
    print("OK — model responded with Luau-looking code:\n")
    print(text)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"SMOKE TEST FAILED: {e}", file=sys.stderr)
        sys.exit(1)
