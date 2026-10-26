# Uzhavan.AI — On-Device Crop Grading Model Pipeline

This directory contains the training and export pipeline for the edge AI crop quality classifier deployed to rural Android devices.

## Overview
- **Architecture**: YOLOv8n Classification (`yolov8n-cls.pt`)
- **Classes**: `grade_a`, `grade_b`, `grade_c`, `rejected`
- **Target Device**: 2 GB RAM Android phone, offline CPU inference (<200 ms)
- **Deployment Format**: INT8 quantized TensorFlow Lite (`crop_grader.tflite`)

## Training with Meta AI Augmentation

1. **Dataset Structure**:
   Organize human-captured produce images into ImageFolder format:
   ```
   dataset/
     train/
       grade_a/
       grade_b/
       grade_c/
       rejected/
     val/
       grade_a/
       grade_b/
       grade_c/
       rejected/
   ```

2. **Synthetic Data Augmentation (Muse Image 1.0)**:
   Top up rare defect classes (e.g. rot, pest holes) without altering realistic farm backgrounds:
   ```bash
   export MODEL_API_KEY=your_meta_api_key
   python synthetic_augment.py
   ```

3. **Train the Classifier**:
   ```bash
   pip install -r requirements.txt
   python train_yolo.py --data dataset --epochs 60 --imgsz 224
   ```

4. **Export to INT8 Quantized TFLite**:
   ```bash
   python export_tflite.py --weights runs/uzhavan_grading/train/weights/best.pt --data dataset
   ```
   This automatically places `crop_grader.tflite` and `labels.txt` into `mobile/assets/models/`.
