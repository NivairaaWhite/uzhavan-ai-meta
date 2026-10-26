import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:camera/camera.dart';
import 'package:geolocator/geolocator.dart';
import 'package:uuid/uuid.dart';
import '../services/tflite_service.dart';
import '../services/local_db_service.dart';
import '../models/crop_listing.dart';
import 'results_screen.dart';

/// The core offline flow: point camera at produce -> on-device TFLite
/// grades it -> result is written to Hive immediately, before any network
/// call. This works with the phone in airplane mode.
class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key});
  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  CameraController? _cameraController;
  bool _busy = false;
  String? _cropType = 'tomato';
  final _quantityCtrl = TextEditingController(text: '10');

  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  Future<void> _initCamera() async {
    final cameras = await availableCameras();
    if (cameras.isEmpty) return;
    _cameraController = CameraController(cameras.first, ResolutionPreset.medium);
    await _cameraController!.initialize();
    if (mounted) setState(() {});
  }

  Future<void> _captureAndGrade() async {
    final tflite = context.read<TfliteService>();
    if (!tflite.isLoaded) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Grading model not loaded yet — see ai_model/README.md')),
      );
      return;
    }
    if (_cameraController == null || !_cameraController!.value.isInitialized) return;

    setState(() => _busy = true);
    try {
      final picture = await _cameraController!.takePicture();
      final (grade, confidence) = await tflite.classify(File(picture.path));

      Position? position;
      try {
        position = await Geolocator.getCurrentPosition();
      } catch (_) {
        // GPS unavailable indoors/underground — fall back to last known
        // fix so a scan is never blocked entirely on location.
        position = await Geolocator.getLastKnownPosition();
      }

      final listing = CropListing(
        offlineScanUuid: const Uuid().v4(),
        cropType: _cropType ?? 'unknown',
        grade: grade,
        gradeConfidence: confidence,
        quantityKg: double.tryParse(_quantityCtrl.text) ?? 0,
        latitude: position?.latitude ?? 0,
        longitude: position?.longitude ?? 0,
        scanImageRef: picture.path,
        createdAt: DateTime.now(),
      );

      await context.read<LocalDbService>().saveListing(listing);

      if (!mounted) return;
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => ResultsScreen(listing: listing)),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  void dispose() {
    _cameraController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scan Crop')),
      body: Column(
        children: [
          Expanded(
            child: _cameraController?.value.isInitialized == true
                ? CameraPreview(_cameraController!)
                : const Center(child: CircularProgressIndicator()),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                DropdownButtonFormField<String>(
                  initialValue: _cropType,
                  decoration: const InputDecoration(labelText: 'Crop type'),
                  items: const [
                    DropdownMenuItem(value: 'tomato', child: Text('Tomato')),
                    DropdownMenuItem(value: 'onion', child: Text('Onion')),
                    DropdownMenuItem(value: 'paddy', child: Text('Paddy')),
                    DropdownMenuItem(value: 'brinjal', child: Text('Brinjal')),
                    DropdownMenuItem(value: 'banana', child: Text('Banana')),
                    DropdownMenuItem(value: 'chilli', child: Text('Chilli')),
                  ],
                  onChanged: (v) => setState(() => _cropType = v),
                ),
                TextField(
                  controller: _quantityCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Quantity (kg)'),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: _busy ? null : _captureAndGrade,
                    icon: const Icon(Icons.camera),
                    label: Text(_busy ? 'Grading...' : 'Capture & Grade'),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
