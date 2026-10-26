import 'package:flutter/material.dart';
import '../models/crop_listing.dart';

class ResultsScreen extends StatelessWidget {
  final CropListing listing;
  const ResultsScreen({super.key, required this.listing});

  Color _gradeColor(String grade) {
    switch (grade) {
      case 'grade_a': return Colors.green;
      case 'grade_b': return Colors.orange;
      case 'grade_c': return Colors.deepOrange;
      default: return Colors.red;
    }
  }

  @override
  Widget build(BuildContext context) {
    final confidencePct = ((listing.gradeConfidence ?? 0) * 100).toStringAsFixed(0);
    return Scaffold(
      appBar: AppBar(title: const Text('Scan Result')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Center(
              child: CircleAvatar(
                radius: 60,
                backgroundColor: _gradeColor(listing.grade),
                child: Text(
                  listing.grade.replaceAll('grade_', '').toUpperCase(),
                  style: const TextStyle(fontSize: 32, color: Colors.white, fontWeight: FontWeight.bold),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Center(child: Text('Confidence: $confidencePct%', style: const TextStyle(fontSize: 16))),
            const SizedBox(height: 24),
            _InfoRow(label: 'Crop', value: listing.cropType),
            _InfoRow(label: 'Quantity', value: '${listing.quantityKg} kg'),
            _InfoRow(label: 'Status', value: 'Saved offline — will sync automatically'),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => Navigator.popUntil(context, (r) => r.isFirst),
              child: const Text('Done'),
            ),
          ],
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  const _InfoRow({required this.label, required this.value});
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.grey)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}
