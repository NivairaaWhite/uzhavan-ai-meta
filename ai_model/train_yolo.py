"""
Trains the offline crop-grading classifier.

Usage:
  python train_yolo.py --data dataset --epochs 60 --imgsz 224 --model yolov8n-cls.pt

Needs: a labeled dataset in standard ImageFolder layout:
  dataset/train/grade_a/*.jpg
  dataset/train/grade_b/*.jpg
  dataset/train/grade_c/*.jpg
  dataset/train/rejected/*.jpg
  (and identical structure under dataset/val/)
"""
import argparse
from pathlib import Path

from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(description="Train Ultralytics produce grading classifier")
    parser.add_argument("--data", default="dataset",
                        help="path to ImageFolder dataset directory (not a YAML file)")
    parser.add_argument("--model", default="yolov8n-cls.pt",
                        help="base pretrained classification checkpoint to fine-tune from")
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--imgsz", type=int, default=224)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default=None, help="'cpu', 0, or None to auto-select")
    parser.add_argument("--project", default="runs/uzhavan_grading")
    parser.add_argument("--name", default="train")
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        raise FileNotFoundError(
            f"Dataset directory '{args.data}' not found. Please populate dataset/train and "
            f"dataset/val with grade subdirectories (grade_a, grade_b, grade_c, rejected) "
            f"before training."
        )

    model = YOLO(args.model)
    model.train(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=args.project,
        name=args.name,
        patience=15,        # early stopping if val loss plateaus
        optimizer="AdamW",
        cos_lr=True,
        augment=True,       # data augmentations for real field lighting variations
        val=True,
    )

    metrics = model.val()
    top1_acc = getattr(metrics, "top1", 0.0)
    print(f"Validation Top-1 Accuracy: {top1_acc:.4f}")
    print(f"Best model weights saved to: {args.project}/{args.name}/weights/best.pt")


if __name__ == "__main__":
    main()
