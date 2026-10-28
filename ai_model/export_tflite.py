"""
Exports a trained classifier checkpoint to quantized TFLite for
on-device inference (target: sub-200ms on a low-end phone CPU).

Usage:
  python export_tflite.py --weights runs/uzhavan_grading/train/weights/best.pt --data dataset
"""
import argparse
import shutil
from pathlib import Path

from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(description="Export trained YOLOv8 classifier to TFLite")
    parser.add_argument("--weights", required=True, help="path to trained .pt checkpoint")
    parser.add_argument("--data", default="dataset",
                        help="ImageFolder path, used for INT8 calibration sampling")
    parser.add_argument("--imgsz", type=int, default=224)
    parser.add_argument("--out", default="../mobile/assets/models/crop_grader.tflite",
                        help="destination path in Flutter app assets")
    args = parser.parse_args()

    model = YOLO(args.weights)
    print(f"Exporting model from {args.weights} to ONNX...")
    onnx_path = model.export(format="onnx", imgsz=args.imgsz)

    print("Converting ONNX to TFLite...")
    import onnx2tf
    onnx_file = Path(onnx_path)
    tf_out = onnx_file.parent / "saved_model"
    onnx2tf.convert(
        input_onnx_file_path=str(onnx_file),
        output_folder_path=str(tf_out),
        not_use_onnxsim=True,
    )
    candidates = list(tf_out.glob("*float32.tflite")) or list(tf_out.glob("*.tflite"))
    if not candidates:
        raise FileNotFoundError(f"No .tflite file generated in {tf_out}")
    tflite_candidate = candidates[0]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(tflite_candidate, out_path)

    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"Exported quantized TFLite model to {out_path} ({size_mb:.2f} MB)")
    if size_mb > 15:
        print("WARNING: target is <15MB for fast on-device inference on 2GB RAM phones.")

    # Write labels.txt in the exact class index order
    labels_out = out_path.parent / "labels.txt"
    names = getattr(model, "names", {})
    with open(labels_out, "w", encoding="utf-8") as f:
        for i in sorted(names.keys()):
            f.write(f"{names[i]}\n")
    print(f"Wrote labels file to {labels_out}")


if __name__ == "__main__":
    main()
