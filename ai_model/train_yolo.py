"""
Trains the offline crop-grading detector.

Usage:
  python train_yolo.py --data data.yaml --epochs 100 --imgsz 224 --model yolov8n.pt

Needs: a labeled dataset matching data.yaml's layout (see that file's
header comment), and a GPU for anything beyond a tiny smoke test — a
T4 via Colab/Kaggle or an AWS g4dn.xlarge, per the blueprint's own
sizing. This script does not include a dataset; obtaining and labeling
real crop-quality images (Roboflow / Label Studio, per the blueprint) is
a separate, necessarily manual step no code can substitute for.
"""
import argparse
from pathlib import Path

from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data.yaml")
    parser.add_argument("--model", default="yolov8n.pt", help="base checkpoint to fine-tune from")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=224)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default=None, help="'cpu', 0, or None to auto-select")
    parser.add_argument("--project", default="runs/uzhavan_grading")
    parser.add_argument("--name", default="train")
    args = parser.parse_args()

    if not Path(args.data).exists():
        raise FileNotFoundError(
            f"{args.data} not found. This script trains on real labeled crop "
            "images — see README.md for how to source and label a dataset "
            "before running this for real."
        )

    model = YOLO(args.model)
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=args.project,
        name=args.name,
        patience=15,        # early stop if val loss plateaus — avoids overfitting small ag datasets
        optimizer="AdamW",
        cos_lr=True,
        augment=True,       # crop photos in the field vary hugely in lighting/angle
        val=True,
    )

    metrics = model.val()
    print(f"mAP50-95: {metrics.box.map:.4f}")
    print(f"Best weights saved under: {args.project}/{args.name}/weights/best.pt")


if __name__ == "__main__":
    main()
