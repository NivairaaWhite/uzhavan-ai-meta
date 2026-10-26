import 'dart:io';
import 'package:flutter/services.dart' show rootBundle;
import 'package:tflite_flutter/tflite_flutter.dart';
import 'package:image/image.dart' as img;

/// On-device crop grading. Loads the quantized INT8 model shipped in
/// assets/models/crop_grader.tflite (see ai_model/ for the training +
/// export pipeline that produces this file). Runs entirely offline —
/// this is the "works with zero network" half of the app.
///
/// NOTE: crop_grader.tflite is NOT included in this repo — a model file
/// only becomes meaningful once trained on real, labeled crop-quality
/// images (see ai_model/README.md). Ship a placeholder or gate scanning
/// behind a "model not loaded" state until you've trained and dropped in
/// a real .tflite file here.
class TfliteService {
  static const String modelPath = 'assets/models/crop_grader.tflite';
  static const String labelsPath = 'assets/models/labels.txt';
  static const int inputSize = 224; // matches ai_model/train_yolo.py imgsz for the classifier head

  Interpreter? _interpreter;
  List<String> _labels = [];

  bool get isLoaded => _interpreter != null;

  Future<void> loadModel() async {
    try {
      _interpreter = await Interpreter.fromAsset(modelPath);
      // Bundled assets live in the app bundle, not the filesystem — must
      // go through rootBundle, not dart:io File.
      final raw = await rootBundle.loadString(labelsPath);
      _labels = raw.split('\n').where((l) => l.trim().isNotEmpty).toList();
    } catch (e) {
      // Model not present yet — app still runs, scanning is just disabled
      // until ai_model/export_tflite.py output is added to assets/.
      _interpreter = null;
    }
  }

  /// Returns (grade, confidence). Throws if the model isn't loaded — the
  /// UI should check [isLoaded] first and show a clear "model not ready"
  /// state instead of calling this blindly.
  Future<(String, double)> classify(File imageFile) async {
    if (_interpreter == null) {
      throw StateError('TFLite model not loaded — see ai_model/README.md');
    }
    final bytes = await imageFile.readAsBytes();
    final decoded = img.decodeImage(bytes);
    if (decoded == null) throw Exception('Could not decode image');

    final resized = img.copyResize(decoded, width: inputSize, height: inputSize);
    final input = _imageToByteListFloat32(resized);
    final output = List.filled(_labels.length, 0.0).reshape([1, _labels.length]);

    _interpreter!.run(input, output);

    final scores = (output[0] as List<double>);
    var bestIdx = 0;
    for (var i = 1; i < scores.length; i++) {
      if (scores[i] > scores[bestIdx]) bestIdx = i;
    }
    return (_labels[bestIdx], scores[bestIdx]);
  }

  List<List<List<List<double>>>> _imageToByteListFloat32(img.Image image) {
    return [
      List.generate(
        inputSize,
        (y) => List.generate(inputSize, (x) {
          final pixel = image.getPixel(x, y);
          return [pixel.r / 255.0, pixel.g / 255.0, pixel.b / 255.0];
        }),
      ),
    ];
  }

  void dispose() => _interpreter?.close();
}
