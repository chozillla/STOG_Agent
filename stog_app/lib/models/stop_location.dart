class StopLocation {
  final String name;
  final String extId;
  final double lat;
  final double lon;

  StopLocation({
    required this.name,
    required this.extId,
    required this.lat,
    required this.lon,
  });

  factory StopLocation.fromJson(Map<String, dynamic> json) {
    return StopLocation(
      name: json['name'] ?? '',
      extId: json['extId'] ?? '',
      lat: _toDouble(json['lat']),
      lon: _toDouble(json['lon']),
    );
  }

  static double _toDouble(dynamic v) {
    if (v is double) return v;
    if (v is int) return v.toDouble();
    if (v is String) return double.tryParse(v) ?? 0.0;
    return 0.0;
  }
}
