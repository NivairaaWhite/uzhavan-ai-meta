/// Mirrors backend/app/schemas.py's AllocationOut /
/// PostHarvestRecommendationOut — the response shape of
/// POST /post-harvest/recommend.
class AllocationChannel {
  final String channel; // sell_now | store | process | at_risk
  final double quantityKg;
  final double? unitPricePerKg;
  final double? estimatedValue;
  final String? facilityName;
  final double? distanceKm;
  final String note;

  AllocationChannel({
    required this.channel,
    required this.quantityKg,
    this.unitPricePerKg,
    this.estimatedValue,
    this.facilityName,
    this.distanceKm,
    required this.note,
  });

  factory AllocationChannel.fromJson(Map<String, dynamic> json) => AllocationChannel(
        channel: json['channel'] as String,
        quantityKg: (json['quantity_kg'] as num).toDouble(),
        unitPricePerKg: (json['unit_price_per_kg'] as num?)?.toDouble(),
        estimatedValue: (json['estimated_value'] as num?)?.toDouble(),
        facilityName: json['facility_name'] as String?,
        distanceKm: (json['distance_km'] as num?)?.toDouble(),
        note: json['note'] as String? ?? '',
      );
}

class PostHarvestRecommendation {
  final String id;
  final String cropType;
  final double quantityKg;
  final String perishabilityTier;
  final List<AllocationChannel> allocations;
  final double? wholesalePricePerKg;
  final double? expectedNetValue;
  final double? baselineSellAllTodayValue;
  final double? projectedSavings;
  final List<String> reasoning;

  PostHarvestRecommendation({
    required this.id,
    required this.cropType,
    required this.quantityKg,
    required this.perishabilityTier,
    required this.allocations,
    this.wholesalePricePerKg,
    this.expectedNetValue,
    this.baselineSellAllTodayValue,
    this.projectedSavings,
    required this.reasoning,
  });

  factory PostHarvestRecommendation.fromJson(Map<String, dynamic> json) => PostHarvestRecommendation(
        id: json['id'] as String? ?? '',
        cropType: json['crop_type'] as String,
        quantityKg: (json['quantity_kg'] as num).toDouble(),
        perishabilityTier: json['perishability_tier'] as String,
        allocations: (json['allocations'] as List)
            .map((a) => AllocationChannel.fromJson(a as Map<String, dynamic>))
            .toList(),
        wholesalePricePerKg: (json['wholesale_price_per_kg'] as num?)?.toDouble(),
        expectedNetValue: (json['expected_net_value'] as num?)?.toDouble(),
        baselineSellAllTodayValue: (json['baseline_sell_all_today_value'] as num?)?.toDouble(),
        projectedSavings: (json['projected_savings'] as num?)?.toDouble(),
        reasoning: (json['reasoning'] as List).map((r) => r as String).toList(),
      );
}
