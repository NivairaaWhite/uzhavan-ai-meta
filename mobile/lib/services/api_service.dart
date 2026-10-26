import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../models/crop_listing.dart';
import 'local_db_service.dart';

/// Thin REST client over the FastAPI backend.
class ApiService {
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  final _storage = const FlutterSecureStorage();
  final LocalDbService localDb;

  ApiService(this.localDb);

  Future<String?> token() => _storage.read(key: 'access_token');

  Future<Map<String, String>> _authHeaders() async {
    final t = await token();
    return {
      'Content-Type': 'application/json',
      if (t != null) 'Authorization': 'Bearer $t',
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
    final t = jsonDecode(resp.body)['access_token'] as String;
    await _storage.write(key: 'access_token', value: t);
  }

  /// Flushes unsynced listings to POST /crop-listings/sync in batch.
  /// Returns list of maps with {'serverId': id, 'scanImageRef': path}.
  Future<List<Map<String, String>>> syncQueuedListings() async {
    final unsynced = localDb.getUnsyncedListings();
    if (unsynced.isEmpty) return [];

    final resp = await http.post(
      Uri.parse('$baseUrl/crop-listings/sync'),
      headers: await _authHeaders(),
      body: jsonEncode({'listings': unsynced.map((l) => l.toJson()).toList()}),
    );
    if (resp.statusCode != 200) {
      throw Exception('Sync failed: ${resp.body}');
    }
    final serverListings = jsonDecode(resp.body) as List;
    final uploadedPairs = <Map<String, String>>[];

    for (final raw in serverListings) {
      final json = raw as Map<String, dynamic>;
      final uuid = json['offline_scan_uuid'] as String?;
      final id = json['id'] as String?;
      if (uuid != null && id != null) {
        await localDb.markSynced(uuid, id);
        final local = unsynced.where((l) => l.offlineScanUuid == uuid).firstOrNull;
        if (local?.scanImageRef != null) {
          uploadedPairs.add({'serverId': id, 'scanImageRef': local!.scanImageRef!});
        }
      }
    }
    return uploadedPairs;
  }

  /// Uploads scan image to the backend for server-side AI audit.
  Future<void> uploadScanImage(String listingId, String imagePath) async {
    final t = await token();
    final uri = Uri.parse('$baseUrl/crop-listings/$listingId/image');
    final request = http.MultipartRequest('POST', uri);
    if (t != null) {
      request.headers['Authorization'] = 'Bearer $t';
    }
    request.files.add(await http.MultipartFile.fromPath('file', imagePath));
    final streamed = await request.send();
    if (streamed.statusCode != 200) {
      throw Exception('Image upload failed: code ${streamed.statusCode}');
    }
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

  /// POST /post-harvest/recommend
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

  /// GET /post-harvest/{rec_id}/explanation
  Future<Map<String, dynamic>> fetchExplanation(String recId, {String lang = 'ta'}) async {
    final resp = await http.get(
      Uri.parse('$baseUrl/post-harvest/$recId/explanation?lang=$lang'),
      headers: await _authHeaders(),
    );
    if (resp.statusCode != 200) {
      return {'explanation': null, 'lang': lang};
    }
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  /// POST /voice/intent
  Future<Map<String, dynamic>> parseVoiceIntent(String transcript) async {
    final resp = await http.post(
      Uri.parse('$baseUrl/voice/intent'),
      headers: await _authHeaders(),
      body: jsonEncode({'transcript': transcript}),
    );
    if (resp.statusCode != 200) {
      throw Exception('Voice intent extraction failed: ${resp.body}');
    }
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  /// POST /agent/ask
  Future<Map<String, dynamic>> askAgent(String question, {double lat = 11.0, double lng = 77.0}) async {
    final resp = await http.post(
      Uri.parse('$baseUrl/agent/ask'),
      headers: await _authHeaders(),
      body: jsonEncode({
        'question': question,
        'latitude': lat,
        'longitude': lng,
      }),
    );
    if (resp.statusCode != 200) {
      throw Exception('Agent error: ${resp.body}');
    }
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }
}
