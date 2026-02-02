import 'package:flutter/material.dart';
import 'package:latlong2/latlong.dart';
import '../utils/time_helpers.dart';
import '../utils/colors.dart';

class TripLeg {
  final String name;
  final String type;
  final Color color;
  final List<LatLng> coordinates;

  TripLeg({
    required this.name,
    required this.type,
    required this.color,
    required this.coordinates,
  });

  bool get isWalk => type == 'WALK';
}

class TripResult {
  final int index;
  final String departureStr;
  final String arrivalStr;
  final String durationStr;
  final int durationMinutes;
  final int transfers;
  final List<TripLeg> legs;
  // Detailed timing for trips screen
  final DateTime? depScheduled;
  final DateTime? depRealtime;
  final DateTime? arrScheduled;
  final DateTime? arrRealtime;
  final bool cancelled;
  final List<Map<String, dynamic>> rawLegs;

  TripResult({
    required this.index,
    required this.departureStr,
    required this.arrivalStr,
    required this.durationStr,
    required this.durationMinutes,
    required this.transfers,
    required this.legs,
    this.depScheduled,
    this.depRealtime,
    this.arrScheduled,
    this.arrRealtime,
    this.cancelled = false,
    this.rawLegs = const [],
  });

  DateTime? get depEffective => depRealtime ?? depScheduled;
  DateTime? get arrEffective => arrRealtime ?? arrScheduled;
}

List<TripLeg> extractPolylines(Map<String, dynamic> trip) {
  var legs = trip['LegList']?['Leg'];
  if (legs == null) return [];
  if (legs is Map) legs = [legs];
  final List legsList = legs as List;

  final result = <TripLeg>[];
  int colorIdx = 0;

  for (final leg in legsList) {
    final legType = leg['type'] ?? '';
    final name = legType == 'WALK' ? 'Walk' : (leg['name'] ?? '').toString().trim();

    Map<String, dynamic> pg;
    if (legType == 'WALK') {
      pg = (leg['GisRoute'] ?? {})['polylineGroup'] ?? {};
    } else {
      pg = leg['PolylineGroup'] ?? {};
    }

    var descs = pg['polylineDesc'];
    if (descs == null) continue;
    if (descs is Map) descs = [descs];

    List<dynamic>? crd;
    for (final desc in descs) {
      final c = desc['crd'];
      if (c != null && c is List && c.length >= 4) {
        crd = c;
        break;
      }
    }
    if (crd == null) continue;

    final coords = <LatLng>[];
    for (int i = 0; i < crd.length - 1; i += 2) {
      final lon = (crd[i] as num).toDouble();
      final lat = (crd[i + 1] as num).toDouble();
      coords.add(LatLng(lat, lon));
    }
    if (coords.length < 2) continue;

    final color = legType == 'WALK'
        ? walkColor
        : transportColors[colorIdx++ % transportColors.length];

    result.add(TripLeg(name: name, type: legType, color: color, coordinates: coords));
  }

  return result;
}

List<TripResult> processTrips(List<dynamic> rawTrips) {
  final results = <TripResult>[];

  for (final trip in rawTrips) {
    final polylines = extractPolylines(trip);

    var legsRaw = trip['LegList']?['Leg'];
    if (legsRaw == null) continue;
    if (legsRaw is Map) legsRaw = [legsRaw];
    final List legsList = legsRaw as List;
    if (legsList.isEmpty) continue;

    final firstLeg = legsList.first;
    final lastLeg = legsList.last;
    final depOrigin = firstLeg['Origin'] ?? {};
    final arrDest = lastLeg['Destination'] ?? {};

    final depDate = depOrigin['date'] ?? '';
    final depTime = depOrigin['time'] ?? '';
    final depRtDate = depOrigin['rtDate'] ?? '';
    final depRtTime = depOrigin['rtTime'] ?? '';
    final arrDate = arrDest['date'] ?? '';
    final arrTime = arrDest['time'] ?? '';
    final arrRtDate = arrDest['rtDate'] ?? '';
    final arrRtTime = arrDest['rtTime'] ?? '';

    if (depTime.isEmpty || arrTime.isEmpty) continue;

    final depScheduled = parseApiTime(depDate, depTime);
    final depRealtime = depRtTime.isNotEmpty ? parseApiTime(depRtDate, depRtTime) : null;
    final arrScheduled = parseApiTime(arrDate, arrTime);
    final arrRealtime = arrRtTime.isNotEmpty ? parseApiTime(arrRtDate, arrRtTime) : null;

    final depEff = depRealtime ?? depScheduled;
    final arrEff = arrRealtime ?? arrScheduled;

    final depStr = formatTimeHHMM(depEff);
    final arrStr = formatTimeHHMM(arrEff);
    final durMin = arrEff.difference(depEff).inMinutes;
    final durStr = formatDuration(durMin);

    final transportLegs = legsList.where((l) => l['type'] != 'WALK').toList();
    final transfers = (transportLegs.length - 1).clamp(0, 99);

    final rawLegsList = legsList.cast<Map<String, dynamic>>();

    results.add(TripResult(
      index: results.length,
      departureStr: depStr,
      arrivalStr: arrStr,
      durationStr: durStr,
      durationMinutes: durMin,
      transfers: transfers,
      legs: polylines.isNotEmpty ? polylines : _fallbackLegs(legsList),
      depScheduled: depScheduled,
      depRealtime: depRealtime,
      arrScheduled: arrScheduled,
      arrRealtime: arrRealtime,
      cancelled: firstLeg['cancelled'] == true,
      rawLegs: List<Map<String, dynamic>>.from(rawLegsList),
    ));
  }

  return results;
}

List<TripLeg> _fallbackLegs(List legsList) {
  int colorIdx = 0;
  return legsList.map((leg) {
    final legType = leg['type'] ?? '';
    final name = legType == 'WALK' ? 'Walk' : (leg['name'] ?? '').toString().trim();
    final color = legType == 'WALK'
        ? walkColor
        : transportColors[colorIdx++ % transportColors.length];
    return TripLeg(name: name, type: legType, color: color, coordinates: []);
  }).toList();
}
