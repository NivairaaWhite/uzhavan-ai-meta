import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import '../models/crop_listing.dart';

class MarketplaceScreen extends StatefulWidget {
  const MarketplaceScreen({super.key});
  @override
  State<MarketplaceScreen> createState() => _MarketplaceScreenState();
}

class _MarketplaceScreenState extends State<MarketplaceScreen> {
  String _cropType = 'tomato';
  late Future<List<CropListing>> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<ApiService>().fetchMarketplace(_cropType);
  }

  void _reload() {
    setState(() => _future = context.read<ApiService>().fetchMarketplace(_cropType));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Marketplace')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: DropdownButtonFormField<String>(
              initialValue: _cropType,
              items: const [
                DropdownMenuItem(value: 'tomato', child: Text('Tomato')),
                DropdownMenuItem(value: 'onion', child: Text('Onion')),
                DropdownMenuItem(value: 'paddy', child: Text('Paddy')),
              ],
              onChanged: (v) {
                if (v == null) return;
                setState(() => _cropType = v);
                _reload();
              },
            ),
          ),
          Expanded(
            child: FutureBuilder<List<CropListing>>(
              future: _future,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasError) {
                  return Center(child: Text('Could not load listings: ${snapshot.error}'));
                }
                final listings = snapshot.data ?? [];
                if (listings.isEmpty) {
                  return const Center(child: Text('No listings yet for this crop'));
                }
                return ListView.builder(
                  itemCount: listings.length,
                  itemBuilder: (context, i) {
                    final l = listings[i];
                    return ListTile(
                      title: Text('${l.quantityKg} kg — ${l.grade.replaceAll('grade_', 'Grade ').toUpperCase()}'),
                      subtitle: Text(l.fairPricePerKg != null
                          ? 'Fair price: ₹${l.fairPricePerKg!.toStringAsFixed(2)}/kg'
                          : 'Price pending'),
                      trailing: const Icon(Icons.chevron_right),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
