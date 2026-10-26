import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:provider/provider.dart';
import '../models/post_harvest_recommendation.dart';
import '../services/api_service.dart';

const _supportedDistricts = [
  'Coimbatore', 'Madurai', 'Salem', 'Erode', 'Tiruchirappalli',
  'Thanjavur', 'Tirunelveli', 'Dindigul', 'Krishnagiri', 'Dharmapuri',
];

/// Post-harvest advisory screen with Tamil voice input, district selector,
/// and AI explanation generation.
class PostHarvestScreen extends StatefulWidget {
  const PostHarvestScreen({super.key});
  @override
  State<PostHarvestScreen> createState() => _PostHarvestScreenState();
}

class _PostHarvestScreenState extends State<PostHarvestScreen> {
  String _cropType = 'tomato';
  final _quantityCtrl = TextEditingController(text: '500');
  String _district = 'Coimbatore';
  bool _loading = false;
  String? _error;
  PostHarvestRecommendation? _result;
  String? _explanation;

  Future<void> _getRecommendation() async {
    final quantity = double.tryParse(_quantityCtrl.text);
    if (quantity == null || quantity <= 0) {
      setState(() => _error = 'Enter a valid quantity in kg');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
      _result = null;
      _explanation = null;
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
            district: _district,
            latitude: position?.latitude ?? 11.0,
            longitude: position?.longitude ?? 77.0,
          );
      if (!mounted) return;
      final rec = PostHarvestRecommendation.fromJson(json);
      setState(() => _result = rec);

      // Asynchronously fetch natural Tamil explanation
      _fetchExplanation(rec.id);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _fetchExplanation(String recId) async {
    try {
      final resp = await context.read<ApiService>().fetchExplanation(recId, lang: 'ta');
      if (mounted && resp['explanation'] != null) {
        setState(() => _explanation = resp['explanation'] as String);
      }
    } catch (_) {}
  }

  Future<void> _handleVoiceInput() async {
    final transcript = await showDialog<String>(
      context: context,
      builder: (ctx) {
        final ctrl = TextEditingController();
        return AlertDialog(
          title: const Text('Speak or Type in Tamil'),
          content: TextField(
            controller: ctrl,
            decoration: const InputDecoration(
              hintText: 'e.g. 500 கிலோ தக்காளி கோயம்புத்தூர்',
            ),
            maxLines: 2,
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
            ElevatedButton(
              onPressed: () => Navigator.pop(ctx, ctrl.text),
              child: const Text('Extract'),
            ),
          ],
        );
      },
    );

    if (transcript != null && transcript.trim().isNotEmpty) {
      try {
        final intent = await context.read<ApiService>().parseVoiceIntent(transcript);
        setState(() {
          if (intent['crop_type'] != null) _cropType = intent['crop_type'];
          if (intent['quantity_kg'] != null) _quantityCtrl.text = intent['quantity_kg'].toString();
          if (intent['district'] != null && _supportedDistricts.contains(intent['district'])) {
            _district = intent['district'];
          }
        });
      } catch (e) {
        setState(() => _error = 'Voice extraction: $e');
      }
    }
  }

  @override
  void dispose() {
    _quantityCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Post-Harvest Advisor')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Row(
            children: [
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: _cropType,
                  decoration: const InputDecoration(labelText: 'Crop type'),
                  items: const [
                    DropdownMenuItem(value: 'tomato', child: Text('Tomato (தக்காளி)')),
                    DropdownMenuItem(value: 'onion', child: Text('Onion (வெங்காயம்)')),
                    DropdownMenuItem(value: 'paddy', child: Text('Paddy (நெல்)')),
                    DropdownMenuItem(value: 'brinjal', child: Text('Brinjal (கத்தரிக்காய்)')),
                    DropdownMenuItem(value: 'banana', child: Text('Banana (வாழை)')),
                    DropdownMenuItem(value: 'chilli', child: Text('Chilli (மிளகாய்)')),
                  ],
                  onChanged: (v) => setState(() => _cropType = v ?? _cropType),
                ),
              ),
              const SizedBox(width: 8),
              IconButton.filledTonal(
                icon: const Icon(Icons.mic),
                onPressed: _handleVoiceInput,
                tooltip: 'Speak in Tamil',
              ),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _quantityCtrl,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'Quantity harvested (kg)'),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            value: _district,
            decoration: const InputDecoration(labelText: 'District'),
            items: _supportedDistricts
                .map((d) => DropdownMenuItem(value: d, child: Text(d)))
                .toList(),
            onChanged: (v) => setState(() => _district = v ?? _district),
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _loading ? null : _getRecommendation,
              icon: const Icon(Icons.query_stats),
              label: Text(_loading ? 'Consulting Advisor...' : 'What should I do with this?'),
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: const TextStyle(color: Colors.red)),
          ],
          if (_explanation != null) ...[
            const SizedBox(height: 16),
            Card(
              color: Colors.green.shade50,
              elevation: 0,
              shape: RoundedRectangleBorder(
                side: BorderSide(color: Colors.green.shade200),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.auto_awesome, color: Colors.green.shade800, size: 20),
                        const SizedBox(width: 8),
                        Text(
                          'AI Tamil Explanation',
                          style: TextStyle(fontWeight: FontWeight.bold, color: Colors.green.shade900),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(_explanation!, style: const TextStyle(fontSize: 15, height: 1.4)),
                  ],
                ),
              ),
            ),
          ],
          if (_result != null) ...[
            const SizedBox(height: 20),
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
      default: return Colors.red;
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
      case 'sell_now': return 'Sell Today';
      case 'store': return 'Cold Storage';
      case 'process': return 'Processing Unit';
      default: return 'At Risk';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          '${result.quantityKg.toStringAsFixed(0)} kg ${result.cropType.toUpperCase()}',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 10),
        for (final a in result.allocations)
          Card(
            margin: const EdgeInsets.only(bottom: 8),
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor: _channelColor(a.channel),
                child: Icon(_channelIcon(a.channel), color: Colors.white, size: 20),
              ),
              title: Text('${_channelLabel(a.channel)} — ${a.quantityKg.toStringAsFixed(0)} kg'),
              subtitle: Text(a.note),
              trailing: a.estimatedValue != null
                  ? Text('₹${a.estimatedValue!.toStringAsFixed(0)}',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16))
                  : null,
            ),
          ),
        if (result.expectedNetValue != null) ...[
          const SizedBox(height: 8),
          _ValueRow(label: 'Net value with this plan', value: result.expectedNetValue!),
          if (result.baselineSellAllTodayValue != null)
            _ValueRow(label: 'Baseline distress value', value: result.baselineSellAllTodayValue!),
          if (result.projectedSavings != null)
            _ValueRow(
              label: 'Extra income gained',
              value: result.projectedSavings!,
              highlight: true,
            ),
        ],
        const SizedBox(height: 16),
        ExpansionTile(
          title: const Text('Why this plan? (Rules reasoning)'),
          children: result.reasoning
              .map((r) => Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('• '),
                        Expanded(child: Text(r)),
                      ],
                    ),
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
              fontSize: 15,
              color: highlight ? Colors.green[800] : null,
            ),
          ),
        ],
      ),
    );
  }
}
