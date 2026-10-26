import 'package:hive_flutter/hive_flutter.dart';
import '../models/crop_listing.dart';

/// Offline-first storage. Every scan is written here FIRST, synchronously,
/// before any network call is attempted — this is what makes the app work
/// with zero connectivity in the field (the core requirement in the
/// blueprint). ApiService.syncQueuedListings() later flushes unsynced rows.
class LocalDbService {
  static const _boxName = 'crop_listings_box';
  late Box _box;

  Future<void> init() async {
    await Hive.initFlutter();
    _box = await Hive.openBox(_boxName);
  }

  Future<void> saveListing(CropListing listing) async {
    await _box.put(listing.offlineScanUuid, listing.toHiveMap());
  }

  List<CropListing> getAllListings() {
    return _box.values
        .map((raw) => CropListing.fromHiveMap(raw as Map))
        .toList()
      ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
  }

  List<CropListing> getUnsyncedListings() {
    return getAllListings().where((l) => !l.synced).toList();
  }

  Future<void> markSynced(String offlineScanUuid, String serverId) async {
    final raw = _box.get(offlineScanUuid);
    if (raw == null) return;
    final map = Map<String, dynamic>.from(raw as Map);
    map['synced'] = true;
    map['id'] = serverId;
    await _box.put(offlineScanUuid, map);
  }

  int get unsyncedCount => getUnsyncedListings().length;
}
