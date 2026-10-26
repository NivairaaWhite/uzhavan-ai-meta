import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import '../services/api_service.dart';
import '../services/local_db_service.dart';

/// Explicit sync screen allowing farmers on 2G connections to control
/// data consumption while syncing scan records and uploading produce photos.
class SyncScreen extends StatefulWidget {
  const SyncScreen({super.key});
  @override
  State<SyncScreen> createState() => _SyncScreenState();
}

class _SyncScreenState extends State<SyncScreen> {
  bool _syncing = false;
  bool _uploadPhotos = true;
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
      final syncedPairs = await api.syncQueuedListings();

      String msg = 'Synced ${syncedPairs.length} listing(s) successfully.';

      if (_uploadPhotos && syncedPairs.isNotEmpty) {
        int uploadedCount = 0;
        for (final pair in syncedPairs) {
          try {
            await api.uploadScanImage(pair['serverId']!, pair['scanImageRef']!);
            uploadedCount++;
          } catch (_) {
            // Photo upload is best-effort and non-blocking
          }
        }
        msg += ' Uploaded $uploadedCount photo(s) for AI grade audit.';
      }

      setState(() => _message = msg);
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
      appBar: AppBar(title: const Text('Sync Data')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                Text('${unsynced.length} scan(s) waiting to sync', style: const TextStyle(fontSize: 16)),
                const SizedBox(height: 8),
                SwitchListTile(
                  title: const Text('Upload photos for AI audit'),
                  subtitle: const Text('Uses ~200 KB per photo on 2G/3G'),
                  value: _uploadPhotos,
                  onChanged: (v) => setState(() => _uploadPhotos = v),
                ),
                const SizedBox(height: 8),
                ElevatedButton.icon(
                  onPressed: _syncing ? null : _sync,
                  icon: _syncing
                      ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.sync),
                  label: Text(_syncing ? 'Syncing...' : 'Sync now'),
                ),
                if (_message != null) ...[
                  const SizedBox(height: 12),
                  Text(_message!, style: const TextStyle(color: Colors.green, fontWeight: FontWeight.bold)),
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
                  title: Text('${l.cropType} — ${l.quantityKg} kg (Grade ${l.grade.replaceAll('grade_', '').toUpperCase()})'),
                  subtitle: Text('Scanned: ${l.createdAt.toLocal().toString().split('.')[0]}'),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
