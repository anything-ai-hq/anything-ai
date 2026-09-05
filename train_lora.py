"""LoRA fine-tune Qwen2.5-Coder-1.5B-Instruct on the Luau corpus.

Usage: python train_lora.py [--data data/luau_corpus.jsonl] [--epochs N]
"""
import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

from datasets import Dataset
from unsloth import FastLanguageModel
from trl import SFTTrainer, SFTConfig

BASE_MODEL = "unsloth/Qwen2.5-Coder-1.5B-Instruct"
MAX_SEQ_LEN = 1024  # RTX 5050 laptop = 8GB shared VRAM, keep headroom


def load_dataset(path: str) -> Dataset:
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows, f"No examples in {path}"

    def to_text(row):
        return {
            "text": (
                f"### Instruction:\n{row['prompt']}\n\n"
                f"### Response:\n```luau\n{row['completion']}\n```"
            )
        }

    return Dataset.from_list(rows).map(to_text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/luau_corpus.jsonl")
    parser.add_argument("--epochs", type=int, default=None, help="default: 3 if <2000 examples else 1")
    parser.add_argument("--out", default="adapters/luau-lora")
    args = parser.parse_args()

    dataset = load_dataset(args.data)
    epochs = args.epochs or (3 if len(dataset) < 2000 else 1)
    print(f"Training on {len(dataset)} examples for {epochs} epoch(s).")

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL,
        max_seq_length=MAX_SEQ_LEN,
        load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LEN,
        args=SFTConfig(
            per_device_train_batch_size=1,
            gradient_accumulation_steps=8,
            num_train_epochs=epochs,
            learning_rate=2e-4,
            fp16=not FastLanguageModel.is_bfloat16_supported() if hasattr(FastLanguageModel, "is_bfloat16_supported") else False,
            bf16=True,
            logging_steps=10,
            output_dir="outputs",
            save_strategy="steps",
            save_steps=30,
            save_total_limit=1,
            report_to="none",
        ),
    )
    trainer.train()

    out_path = Path(args.out)
    out_path.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(out_path))
    tokenizer.save_pretrained(str(out_path))
    print(f"Adapter saved to {out_path}")


if __name__ == "__main__":
    main()
