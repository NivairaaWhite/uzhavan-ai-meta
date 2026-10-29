import 'package:flutter/material.dart';
import '../models/crop_listing.dart';
import '../app_localizations.dart';

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

  Widget _auditBadge(BuildContext context) {
    if (listing.auditStatus == null || listing.auditStatus == 'none') {
      return const SizedBox.shrink();
    }
    Color color;
    String label;
    IconData icon;
    switch (listing.auditStatus) {
      case 'agree':
        color = Colors.green;
        label = AppLocalizations.of(context)?.translate('verified_by_meta_ai') ?? 'Verified by Meta AI';
        icon = Icons.verified;
        break;
      case 'disagree':
        color = Colors.amber.shade900;
        label = AppLocalizations.of(context)?.translate('audit_disagree') ?? 'AI Audit Flagged — Please Re-scan';
        icon = Icons.warning_amber_rounded;
        break;
      case 'pending':
        color = Colors.blue;
        label = AppLocalizations.of(context)?.translate('audit_pending') ?? 'AI Audit Pending';
        icon = Icons.hourglass_top;
        break;
      default:
        color = Colors.grey;
        label = 'Audit: ${listing.auditStatus}';
        icon = Icons.info_outline;
    }
    return Container(
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color, width: 1.5),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(width: 6),
          Text(label, style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 13)),
        ],
      ),
    );
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
            Center(child: Text('On-device Confidence: $confidencePct%', style: const TextStyle(fontSize: 16))),
            Center(child: _auditBadge(context)),
            const SizedBox(height: 24),
            _InfoRow(label: 'Crop', value: listing.cropType),
            _InfoRow(label: 'Quantity', value: '${listing.quantityKg} kg'),
            _InfoRow(label: 'Status', value: listing.synced ? 'Synced to Server' : 'Saved offline — ready to sync'),
            if (listing.auditGrade != null && listing.auditGrade != listing.grade)
              _InfoRow(label: 'Server Audit Verdict', value: listing.auditGrade!.replaceAll('grade_', 'Grade ').toUpperCase()),
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
