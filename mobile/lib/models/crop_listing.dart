/// Mirrors the backend's CropListing schema plus on-device state
/// (sync state, local offline uuid, server audit verdict).
class CropListing {
  final String? id; // null until the server assigns one
  final String offlineScanUuid; // generated on-device, used to dedupe on sync
  final String cropType;
  final String grade; // grade_a | grade_b | grade_c | rejected
  final double? gradeConfidence;
  final double quantityKg;
  final double? targetPricePerKg;
  final double? fairPricePerKg;
  final String? district;
  final double latitude;
  final double longitude;
  final String? scanImageRef;
  final DateTime createdAt;
  bool synced;
  bool imageUploaded;

  // Server AI grade audit fields
  final String? auditStatus; // none | pending | agree | disagree | skipped
  final String? auditGrade;
  final double? auditConfidence;

  CropListing({
    this.id,
    required this.offlineScanUuid,
    required this.cropType,
    required this.grade,
    this.gradeConfidence,
    required this.quantityKg,
    this.targetPricePerKg,
    this.fairPricePerKg,
    this.district,
    required this.latitude,
    required this.longitude,
    this.scanImageRef,
    required this.createdAt,
    this.synced = false,
    this.imageUploaded = false,
    this.auditStatus,
    this.auditGrade,
    this.auditConfidence,
  });

  Map<String, dynamic> toJson() => {
        'crop_type': cropType,
        'grade': grade,
        'grade_confidence': gradeConfidence,
        'quantity_kg': quantityKg,
        'target_price_per_kg': targetPricePerKg,
        'district': district,
        'latitude': latitude,
        'longitude': longitude,
        'scan_image_ref': scanImageRef,
        'offline_scan_uuid': offlineScanUuid,
      };

  factory CropListing.fromJson(Map<String, dynamic> json) => CropListing(
        id: json['id'] as String?,
        offlineScanUuid: json['offline_scan_uuid'] as String? ?? '',
        cropType: json['crop_type'] as String,
        grade: json['grade'] as String,
        gradeConfidence: (json['grade_confidence'] as num?)?.toDouble(),
        quantityKg: (json['quantity_kg'] as num).toDouble(),
        targetPricePerKg: (json['target_price_per_kg'] as num?)?.toDouble(),
        fairPricePerKg: (json['fair_price_per_kg'] as num?)?.toDouble(),
        district: json['district'] as String?,
        latitude: (json['latitude'] as num).toDouble(),
        longitude: (json['longitude'] as num).toDouble(),
        scanImageRef: json['scan_image_ref'] as String?,
        createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
        synced: json['id'] != null,
        auditStatus: json['audit_status'] as String? ?? 'none',
        auditGrade: json['audit_grade'] as String?,
        auditConfidence: (json['audit_confidence'] as num?)?.toDouble(),
      );

  Map<String, dynamic> toHiveMap() => {
        'id': id,
        'offlineScanUuid': offlineScanUuid,
        'cropType': cropType,
        'grade': grade,
        'gradeConfidence': gradeConfidence,
        'quantityKg': quantityKg,
        'targetPricePerKg': targetPricePerKg,
        'fairPricePerKg': fairPricePerKg,
        'district': district,
        'latitude': latitude,
        'longitude': longitude,
        'scanImageRef': scanImageRef,
        'createdAt': createdAt.toIso8601String(),
        'synced': synced,
        'imageUploaded': imageUploaded,
        'auditStatus': auditStatus,
        'auditGrade': auditGrade,
        'auditConfidence': auditConfidence,
      };

  factory CropListing.fromHiveMap(Map<dynamic, dynamic> map) => CropListing(
        id: map['id'] as String?,
        offlineScanUuid: map['offlineScanUuid'] as String,
        cropType: map['cropType'] as String,
        grade: map['grade'] as String,
        gradeConfidence: map['gradeConfidence'] as double?,
        quantityKg: map['quantityKg'] as double,
        targetPricePerKg: map['targetPricePerKg'] as double?,
        fairPricePerKg: map['fairPricePerKg'] as double?,
        district: map['district'] as String?,
        latitude: map['latitude'] as double,
        longitude: map['longitude'] as double,
        scanImageRef: map['scanImageRef'] as String?,
        createdAt: DateTime.parse(map['createdAt'] as String),
        synced: map['synced'] as bool? ?? false,
        imageUploaded: map['imageUploaded'] as bool? ?? false,
        auditStatus: map['auditStatus'] as String? ?? 'none',
        auditGrade: map['auditGrade'] as String?,
        auditConfidence: map['auditConfidence'] as double?,
      );
}
