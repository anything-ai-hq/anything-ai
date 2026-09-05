"""Merge LoRA adapter into base model and export quantized GGUF for Ollama.

Usage: python export_gguf.py [--adapter adapters/luau-lora] [--out models]
"""
import argparse
from pathlib import Path

from unsloth import FastLanguageModel

BASE_MODEL = "unsloth/Qwen2.5-Coder-1.5B-Instruct"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", default="adapters/luau-lora")
    parser.add_argument("--out", default="models")
    parser.add_argument("--quant", default="q4_k_m")
    args = parser.parse_args()

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.adapter,
        max_seq_length=2048,
        load_in_4bit=True,
    )

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained_gguf(str(out_dir), tokenizer, quantization_method=args.quant)
    print(f"GGUF exported under {out_dir} (quant={args.quant})")


if __name__ == "__main__":
    main()
