import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import '../services/api_service.dart';
import '../services/local_db_service.dart';

/// Explicit sync screen so a farmer can SEE what's queued and trigger a
/// sync manually (important on 2G, where you don't want silent background
/// syncs eating a scarce/expensive data budget without the user knowing).
class SyncScreen extends StatefulWidget {
  const SyncScreen({super.key});
  @override
  State<SyncScreen> createState() => _SyncScreenState();
}

class _SyncScreenState extends State<SyncScreen> {
  bool _syncing = false;
  String? _message;

  Future<void> _sync() async {
    setState(() { _syncing = true; _message = null; });
    try {
      final connectivity = await Connectivity().checkConnectivity();
      if (connectivity.contains(ConnectivityResult.none)) {
        setState(() => _message = 'No network connection. Try again when you have signal.');
        return;
      }
      final api = context.read<ApiService>();
      final count = await api.syncQueuedListings();
      setState(() => _message = 'Synced $count listing(s) successfully.');
    } catch (e) {
      setState(() => _message = 'Sync failed: $e');
    } finally {
      if (mounted) setState(() => _syncing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final localDb = context.watch<LocalDbService>();
    final unsynced = localDb.getUnsyncedListings();

    return Scaffold(
      appBar: AppBar(title: const Text('Sync')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                Text('${unsynced.length} scan(s) waiting to sync', style: const TextStyle(fontSize: 16)),
                const SizedBox(height: 12),
                ElevatedButton.icon(
                  onPressed: _syncing ? null : _sync,
                  icon: _syncing
                      ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.sync),
                  label: Text(_syncing ? 'Syncing...' : 'Sync now'),
                ),
                if (_message != null) ...[
                  const SizedBox(height: 12),
                  Text(_message!),
                ],
              ],
            ),
          ),
          const Divider(),
          Expanded(
            child: ListView.builder(
              itemCount: unsynced.length,
              itemBuilder: (context, i) {
                final l = unsynced[i];
                return ListTile(
                  leading: const Icon(Icons.cloud_off, color: Colors.orange),
                  title: Text('${l.cropType} — ${l.quantityKg} kg'),
                  subtitle: Text('Scanned ${l.createdAt}'),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
