"""
Synthetic produce defect generation using Meta Muse Image 1.0 (Phase 2).
Fills rare defect classes (such as severe rot or pest damage) by editing
real farmer photos, preserving lighting, background, and crate contexts.
"""
import os
import base64
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def generate_defect_edits(
    input_dir: str = "dataset/train/grade_a",
    output_dir: str = "dataset/train/rejected",
    prompt: str = "Make about a third of the tomatoes visibly rotten, with soft dark patches and mould. Keep the crate, lighting and background identical.",
    count: int = 50,
):
    api_key = os.environ.get("MODEL_API_KEY")
    if not api_key:
        print("MODEL_API_KEY is not set. Please set MODEL_API_KEY to run synthetic augmentation.")
        return

    if OpenAI is None:
        print("openai package is required to call Meta Model API.")
        return

    client = OpenAI(api_key=api_key, base_url="https://api.meta.ai/v1")
    src_path = Path(input_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    images = list(src_path.glob("*.jpg")) + list(src_path.glob("*.jpeg"))
    if not images:
        print(f"No source images found in {input_dir}")
        return

    print(f"Generating synthetic images using muse-image-1.0...")
    generated = 0
    for src in images[:count]:
        try:
            with open(src, "rb") as f:
                r = client.images.edit(
                    model="muse-image-1.0",
                    image=f,
                    prompt=prompt,
                    n=1,
                )
            item = r.data[0]
            b64_data = getattr(item, "b64_json", None)
            if b64_data:
                target_file = out_path / f"syn_{src.name}"
                target_file.write_bytes(base64.b64decode(b64_data))
                generated += 1
                print(f"Saved synthetic sample: {target_file.name}")
        except Exception as exc:
            print(f"Error augmenting {src.name}: {exc}")

    print(f"Completed: generated {generated} synthetic images in {output_dir}")


if __name__ == "__main__":
    generate_defect_edits()
