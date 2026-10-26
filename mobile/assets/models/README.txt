Placeholder directory.

crop_grader.tflite is intentionally NOT included here — see
ai_model/README.md for how to train one and export_tflite.py, which
copies its output straight into this folder.

labels.txt in this folder is a placeholder matching ai_model/data.yaml's
starting class taxonomy; regenerate it via export_tflite.py once you
have a real trained model (it writes labels.txt from the model's actual
class names, which should match this file but will be authoritative).
