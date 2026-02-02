import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config.dart';
import '../models/stop_location.dart';
import '../models/departure.dart';

class RejseplanenApi {
  final http.Client _client = http.Client();

  Future<Map<String, dynamic>> _get(String endpoint, Map<String, String> params) async {
    params['accessId'] = apiKey;
    params['format'] = 'json';
    final uri = Uri.parse('$baseUrl/$endpoint').replace(queryParameters: params);
    final response = await _client.get(uri, headers: {'User-Agent': 'sTOG-commute/1.0'});
    if (response.statusCode != 200) {
      throw Exception('API error: ${response.statusCode}');
    }
    return json.decode(response.body) as Map<String, dynamic>;
  }

  Future<List<StopLocation>> locationSearch(String query) async {
    final result = await _get('location.name', {'input': query});
    final entries = result['stopLocationOrCoordLocation'] as List? ?? [];
    return entries
        .where((e) => e['StopLocation'] != null)
        .map((e) => StopLocation.fromJson(e['StopLocation']))
        .toList();
  }

  Future<List<dynamic>> searchTrips({
    String? originId,
    String? destId,
    double? originLat,
    double? originLon,
    double? destLat,
    double? destLon,
    int numResults = 6,
    bool poly = false,
  }) async {
    final params = <String, String>{'numF': numResults.toString()};

    if (originLat != null && originLon != null && destLat != null && destLon != null) {
      params['originCoordLat'] = originLat.toString();
      params['originCoordLong'] = originLon.toString();
      params['destCoordLat'] = destLat.toString();
      params['destCoordLong'] = destLon.toString();
    } else {
      if (originId != null) params['originId'] = originId;
      if (destId != null) params['destId'] = destId;
      params['useBus'] = '0';
      params['useMetro'] = '0';
    }

    if (poly) params['poly'] = '1';

    final result = await _get('trip', params);
    var trips = result['Trip'];
    if (trips == null) return [];
    if (trips is Map) return [trips];
    return trips as List;
  }

  Future<List<Departure>> getDepartures(String stationId) async {
    final result = await _get('departureBoard', {'id': stationId});
    var deps = result['Departure'];
    if (deps == null) return [];
    if (deps is Map) deps = [deps];
    return (deps as List).map((d) => Departure.fromJson(d)).toList();
  }

  void dispose() {
    _client.close();
  }
}
