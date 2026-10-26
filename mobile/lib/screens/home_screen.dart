import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/local_db_service.dart';
import 'scan_screen.dart';
import 'marketplace_screen.dart';
import 'sync_screen.dart';
import 'post_harvest_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final localDb = context.watch<LocalDbService>();
    final unsynced = localDb.unsyncedCount;

    return Scaffold(
      appBar: AppBar(title: const Text('Uzhavan.AI')),
      body: GridView.count(
        padding: const EdgeInsets.all(16),
        crossAxisCount: 2,
        mainAxisSpacing: 16,
        crossAxisSpacing: 16,
        children: [
          _HomeTile(
            icon: Icons.camera_alt,
            label: 'Scan Crop',
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ScanScreen())),
          ),
          _HomeTile(
            icon: Icons.storefront,
            label: 'Marketplace',
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const MarketplaceScreen())),
          ),
          _HomeTile(
            icon: Icons.sync,
            label: unsynced > 0 ? 'Sync ($unsynced pending)' : 'Sync (up to date)',
            badge: unsynced > 0,
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SyncScreen())),
          ),
          _HomeTile(
            icon: Icons.local_shipping,
            label: 'Logistics Pools',
            onTap: () {},
          ),
          _HomeTile(
            icon: Icons.query_stats,
            label: 'Post-Harvest Advisor',
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const PostHarvestScreen())),
          ),
        ],
      ),
    );
  }
}

class _HomeTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool badge;
  final VoidCallback onTap;

  const _HomeTile({required this.icon, required this.label, required this.onTap, this.badge = false});

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      child: InkWell(
        onTap: onTap,
        child: Stack(
          children: [
            Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(icon, size: 40),
                  const SizedBox(height: 8),
                  Text(label, textAlign: TextAlign.center),
                ],
              ),
            ),
            if (badge)
              const Positioned(
                top: 12, right: 12,
                child: CircleAvatar(radius: 6, backgroundColor: Colors.orange),
              ),
          ],
        ),
      ),
    );
  }
}
