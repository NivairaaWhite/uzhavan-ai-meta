import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:provider/provider.dart';
import '../models/post_harvest_recommendation.dart';
import '../services/api_service.dart';

/// "What should I do with this crop today?" — calls
/// POST /post-harvest/recommend (see backend/app/routers/post_harvest.py)
/// and shows the resulting sell-now / store / process / at-risk split.
class PostHarvestScreen extends StatefulWidget {
  const PostHarvestScreen({super.key});
  @override
  State<PostHarvestScreen> createState() => _PostHarvestScreenState();
}

class _PostHarvestScreenState extends State<PostHarvestScreen> {
  String _cropType = 'tomato';
  final _quantityCtrl = TextEditingController(text: '500');
  final _districtCtrl = TextEditingController();
  bool _loading = false;
  String? _error;
  PostHarvestRecommendation? _result;

  Future<void> _getRecommendation() async {
    final quantity = double.tryParse(_quantityCtrl.text);
    if (quantity == null || quantity <= 0) {
      setState(() => _error = 'Enter a valid quantity in kg');
      return;
    }
    if (_districtCtrl.text.trim().isEmpty) {
      setState(() => _error = 'Enter your district');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
      _result = null;
    });

    try {
      Position? position;
      try {
        position = await Geolocator.getCurrentPosition();
      } catch (_) {
        position = await Geolocator.getLastKnownPosition();
      }

      final json = await context.read<ApiService>().fetchPostHarvestRecommendation(
            cropType: _cropType,
            quantityKg: quantity,
            district: _districtCtrl.text.trim(),
            latitude: position?.latitude ?? 0,
            longitude: position?.longitude ?? 0,
          );
      if (!mounted) return;
      setState(() => _result = PostHarvestRecommendation.fromJson(json));
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    _quantityCtrl.dispose();
    _districtCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Post-Harvest Advisor')),
      body: ListView(
        padding: const EdgeInsets.all(16),
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
            onChanged: (v) => setState(() => _cropType = v ?? _cropType),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _quantityCtrl,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'Quantity harvested (kg)'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _districtCtrl,
            decoration: const InputDecoration(labelText: 'District (e.g. Coimbatore)'),
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _loading ? null : _getRecommendation,
              icon: const Icon(Icons.query_stats),
              label: Text(_loading ? 'Thinking...' : 'What should I do with this?'),
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: const TextStyle(color: Colors.red)),
          ],
          if (_result != null) ...[
            const SizedBox(height: 24),
            _RecommendationSummary(result: _result!),
          ],
        ],
      ),
    );
  }
}

class _RecommendationSummary extends StatelessWidget {
  final PostHarvestRecommendation result;
  const _RecommendationSummary({required this.result});

  Color _channelColor(String channel) {
    switch (channel) {
      case 'sell_now': return Colors.green;
      case 'store': return Colors.blue;
      case 'process': return Colors.orange;
      default: return Colors.red; // at_risk
    }
  }

  IconData _channelIcon(String channel) {
    switch (channel) {
      case 'sell_now': return Icons.storefront;
      case 'store': return Icons.ac_unit;
      case 'process': return Icons.precision_manufacturing;
      default: return Icons.warning_amber_rounded;
    }
  }

  String _channelLabel(String channel) {
    switch (channel) {
      case 'sell_now': return 'Sell today';
      case 'store': return 'Cold-store';
      case 'process': return 'Send to processing';
      default: return 'At risk of spoilage';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('${result.quantityKg.toStringAsFixed(0)} kg ${result.cropType}',
            style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 12),
        for (final a in result.allocations)
          Card(
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor: _channelColor(a.channel),
                child: Icon(_channelIcon(a.channel), color: Colors.white, size: 20),
              ),
              title: Text('${_channelLabel(a.channel)} — ${a.quantityKg.toStringAsFixed(0)} kg'),
              subtitle: Text(a.note),
              trailing: a.estimatedValue != null
                  ? Text('₹${a.estimatedValue!.toStringAsFixed(0)}',
                      style: const TextStyle(fontWeight: FontWeight.bold))
                  : null,
            ),
          ),
        if (result.expectedNetValue != null) ...[
          const SizedBox(height: 8),
          _ValueRow(label: 'Expected value with this plan', value: result.expectedNetValue!),
          if (result.baselineSellAllTodayValue != null)
            _ValueRow(label: 'If sold with no plan today', value: result.baselineSellAllTodayValue!),
          if (result.projectedSavings != null)
            _ValueRow(
              label: 'Estimated gain from this plan',
              value: result.projectedSavings!,
              highlight: true,
            ),
        ],
        const SizedBox(height: 16),
        ExpansionTile(
          title: const Text('Why this recommendation?'),
          children: result.reasoning
              .map((r) => Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                    child: Text('• $r'),
                  ))
              .toList(),
        ),
      ],
    );
  }
}

class _ValueRow extends StatelessWidget {
  final String label;
  final double value;
  final bool highlight;
  const _ValueRow({required this.label, required this.value, this.highlight = false});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(color: highlight ? Colors.green[800] : Colors.grey[700])),
          Text(
            '₹${value.toStringAsFixed(0)}',
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: highlight ? Colors.green[800] : null,
            ),
          ),
        ],
      ),
    );
  }
}
