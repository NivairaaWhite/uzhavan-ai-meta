# Uzhavan.AI — Edge AI Crop Grading

Trains and exports the on-device YOLOv8 model that grades produce quality
from the phone camera, entirely offline once installed.

## Honesty note on what's here vs. what isn't

This is training **infrastructure**, not a trained model — matching how
the rest of this project was scoped. `train_yolo.py` and
`export_tflite.py` are syntactically verified (`python -m py_compile`)
and written against the real, current Ultralytics YOLOv8 API, but they
were **not run end-to-end** in the environment that built this repo: it
has no GPU and hit a disk-space ceiling installing `torch` for even a
CPU smoke test. Before trusting this pipeline, run a 1-epoch smoke test
yourself on a machine with room to spare:

```bash
pip install -r requirements.txt
python train_yolo.py --data data.yaml --epochs 1 --imgsz 128 --device cpu
```

The much bigger real gap is the same one the original blueprint pointed
at without solving: **no crop-quality image dataset exists yet.**
Nothing can substitute for actually collecting and labeling it.

## What you actually need to do to get a real model

1. **Collect images**: hundreds to low-thousands of photos per crop
   type, covering all six grade classes in `data.yaml`, shot in
   field-realistic lighting (this matters more than resolution — a
   model trained only on clean studio shots will fail outdoors).
2. **Label them**: Roboflow (free tier is enough to start) or
   Label Studio, drawing bounding boxes per the blueprint. Export in
   YOLO format directly into `dataset/images/{train,val}` and
   `dataset/labels/{train,val}`.
3. **Train**: `python train_yolo.py --data data.yaml --epochs 100`
   on a Colab/Kaggle T4 GPU (free tier) or an AWS `g4dn.xlarge`, per the
   blueprint's own sizing.
4. **Export**: `python export_tflite.py --weights runs/.../best.pt`
   — this quantizes to INT8 and drops the result straight into
   `../mobile/assets/models/crop_grader.tflite`, where
   `TfliteService` in the Flutter app already expects it.
5. **Verify on-device latency** on an actual low-end Android phone
   (the <200ms target is a real phone constraint, not something a
   desktop benchmark confirms).

## Files

- `data.yaml` — dataset config + a starting 6-class grading taxonomy
  (not specified in the original blueprint; adjust to what you actually
  label).
- `train_yolo.py` — fine-tunes YOLOv8n on your labeled dataset.
- `export_tflite.py` — quantizes to INT8 TFLite, copies into the mobile
  app's assets, and writes `labels.txt`.
