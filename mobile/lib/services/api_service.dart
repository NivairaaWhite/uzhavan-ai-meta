import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../models/crop_listing.dart';
import 'local_db_service.dart';

/// Thin REST client over the FastAPI backend (see backend/app/main.py for
/// the matching routes). Base URL is the one thing every deployment must
/// change — everything else in this file is environment-agnostic.
class ApiService {
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://api.uzhavan.example', // override at build time:
    // flutter build apk --dart-define=API_BASE_URL=https://your-server
  );

  final _storage = const FlutterSecureStorage();
  final LocalDbService localDb;

  ApiService(this.localDb);

  Future<String?> _token() => _storage.read(key: 'access_token');

  Future<Map<String, String>> _authHeaders() async {
    final token = await _token();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  Future<void> login(String phoneNumber, String password) async {
    final resp = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: {'username': phoneNumber, 'password': password},
    );
    if (resp.statusCode != 200) {
      throw Exception('Login failed: ${resp.body}');
    }
    final token = jsonDecode(resp.body)['access_token'] as String;
    await _storage.write(key: 'access_token', value: token);
  }

  /// Flushes every unsynced local scan to POST /crop-listings/sync in one
  /// batch call, then marks each row synced by matching offline_scan_uuid
  /// against the server's response. Safe to call repeatedly — the backend
  /// dedupes on offline_scan_uuid so a retried sync never double-submits.
  Future<int> syncQueuedListings() async {
    final unsynced = localDb.getUnsyncedListings();
    if (unsynced.isEmpty) return 0;

    final resp = await http.post(
      Uri.parse('$baseUrl/crop-listings/sync'),
      headers: await _authHeaders(),
      body: jsonEncode({'listings': unsynced.map((l) => l.toJson()).toList()}),
    );
    if (resp.statusCode != 200) {
      throw Exception('Sync failed: ${resp.body}');
    }
    final serverListings = jsonDecode(resp.body) as List;
    for (final raw in serverListings) {
      final json = raw as Map<String, dynamic>;
      final uuid = json['offline_scan_uuid'] as String?;
      final id = json['id'] as String?;
      if (uuid != null && id != null) {
        await localDb.markSynced(uuid, id);
      }
    }
    return serverListings.length;
  }

  Future<List<CropListing>> fetchMarketplace(String cropType) async {
    final resp = await http.get(
      Uri.parse('$baseUrl/crop-listings?crop_type=$cropType'),
      headers: await _authHeaders(),
    );
    if (resp.statusCode != 200) throw Exception('Failed to load marketplace');
    final list = jsonDecode(resp.body) as List;
    return list.map((j) => CropListing.fromJson(j as Map<String, dynamic>)).toList();
  }

  Future<Map<String, dynamic>> fetchFairPrice(String cropType, String district) async {
    final resp = await http.get(
      Uri.parse('$baseUrl/market/fair-price?crop_type=$cropType&district=$district'),
      headers: await _authHeaders(),
    );
    if (resp.statusCode != 200) throw Exception('No price data yet');
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  /// Calls POST /post-harvest/recommend (see backend/app/routers/post_harvest.py).
  /// Answers "what should I do with this crop today?" — a sell/store/process
  /// split, not just a single price.
  Future<Map<String, dynamic>> fetchPostHarvestRecommendation({
    required String cropType,
    required double quantityKg,
    required String district,
    required double latitude,
    required double longitude,
    String? listingId,
  }) async {
    final resp = await http.post(
      Uri.parse('$baseUrl/post-harvest/recommend'),
      headers: await _authHeaders(),
      body: jsonEncode({
        'crop_type': cropType,
        'quantity_kg': quantityKg,
        'district': district,
        'latitude': latitude,
        'longitude': longitude,
        'listing_id': listingId,
      }),
    );
    if (resp.statusCode != 200) {
      throw Exception('Could not get a recommendation: ${resp.body}');
    }
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }
}
