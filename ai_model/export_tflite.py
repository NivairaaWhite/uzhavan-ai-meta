"""
Exports a trained checkpoint to quantized INT8 TFLite for on-device
inference (target: sub-200ms on a low-end phone CPU, per the blueprint).

Usage:
  python export_tflite.py --weights runs/uzhavan_grading/train/weights/best.pt

INT8 quantization needs a small representative calibration set (a few
hundred images covering all grade classes) — pass --data so Ultralytics
can sample it from your training set automatically.
"""
import argparse
import shutil
from pathlib import Path

from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", required=True, help="path to trained .pt checkpoint")
    parser.add_argument("--data", default="data.yaml", help="used for INT8 calibration sampling")
    parser.add_argument("--imgsz", type=int, default=224)
    parser.add_argument("--out", default="../mobile/assets/models/crop_grader.tflite",
                         help="copies the exported model straight into the Flutter app's assets/")
    args = parser.parse_args()

    model = YOLO(args.weights)
    exported_path = model.export(format="tflite", int8=True, imgsz=args.imgsz, data=args.data)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(exported_path, out_path)

    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"Exported {out_path} ({size_mb:.1f} MB)")
    if size_mb > 15:
        print("WARNING: blueprint targets <15MB for the on-device model — "
              "consider yolov8n over yolov8s, or a lower imgsz.")

    # labels.txt is what TfliteService in the Flutter app reads at runtime
    labels_out = out_path.parent / "labels.txt"
    names = model.names if hasattr(model, "names") else {}
    with open(labels_out, "w") as f:
        for i in sorted(names.keys()):
            f.write(f"{names[i]}\n")
    print(f"Wrote {labels_out}")


if __name__ == "__main__":
    main()
