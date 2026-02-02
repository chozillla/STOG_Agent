import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../services/rejseplanen_api.dart';
import '../models/trip.dart';
import '../config.dart';
import '../utils/colors.dart';
import '../widgets/trip_card.dart';

// ignore_for_file: unused_element

class MapScreen extends StatefulWidget {
  final RejseplanenApi api;
  const MapScreen({super.key, required this.api});

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  final MapController _mapController = MapController();
  LatLng? _origin;
  LatLng? _destination;
  List<TripResult> _trips = [];
  int _selectedIndex = 0;
  bool _fetching = false;
  String _statusText = 'Tap map to set origin';

  void _onMapTap(TapPosition tapPosition, LatLng point) {
    if (_fetching) return;

    setState(() {
      if (_origin == null) {
        _origin = point;
        _statusText = 'Tap map to set destination';
      } else if (_destination == null) {
        _destination = point;
        _statusText = 'Searching routes...';
        _fetchRoutes();
      } else {
        // Reset
        _origin = point;
        _destination = null;
        _trips = [];
        _selectedIndex = 0;
        _statusText = 'Tap map to set destination';
      }
    });
  }

  void _onOriginDragEnd(DragEndDetails _, LatLng newPos) {
    setState(() { _origin = newPos; });
    if (_destination != null) _fetchRoutes();
  }

  void _onDestDragEnd(DragEndDetails _, LatLng newPos) {
    setState(() { _destination = newPos; });
    _fetchRoutes();
  }

  Future<void> _fetchRoutes() async {
    if (_origin == null || _destination == null) return;
    setState(() { _fetching = true; _statusText = 'Searching routes...'; });

    try {
      final rawTrips = await widget.api.searchTrips(
        originLat: _origin!.latitude,
        originLon: _origin!.longitude,
        destLat: _destination!.latitude,
        destLon: _destination!.longitude,
        poly: true,
        numResults: 6,
      );
      final trips = processTrips(rawTrips);
      setState(() {
        _trips = trips;
        _selectedIndex = 0;
        _fetching = false;
        _statusText = trips.isEmpty
            ? 'No routes found'
            : '${trips.length} route${trips.length > 1 ? 's' : ''} found';
      });
      if (trips.isNotEmpty) _fitBounds();
    } catch (e) {
      setState(() {
        _fetching = false;
        _statusText = 'Error: $e';
      });
    }
  }

  void _fitBounds() {
    if (_trips.isEmpty || _selectedIndex >= _trips.length) return;
    final trip = _trips[_selectedIndex];
    final points = <LatLng>[];
    for (final leg in trip.legs) {
      points.addAll(leg.coordinates);
    }
    if (_origin != null) points.add(_origin!);
    if (_destination != null) points.add(_destination!);
    if (points.length >= 2) {
      final bounds = LatLngBounds.fromPoints(points);
      _mapController.fitCamera(CameraFit.bounds(bounds: bounds, padding: const EdgeInsets.all(50)));
    }
  }

  List<Polyline> _buildPolylines() {
    final polylines = <Polyline>[];
    // Draw deselected routes first, then selected on top
    for (int t = 0; t < _trips.length; t++) {
      if (t == _selectedIndex) continue;
      for (final leg in _trips[t].legs) {
        if (leg.coordinates.length < 2) continue;
        polylines.add(Polyline(
          points: leg.coordinates,
          color: deselectedColor,
          strokeWidth: 3,
          pattern: const StrokePattern.solid(),
        ));
      }
    }
    // Selected route: outline + colored stroke
    if (_selectedIndex < _trips.length) {
      final trip = _trips[_selectedIndex];
      for (final leg in trip.legs) {
        if (leg.coordinates.length < 2) continue;
        // Dark outline behind for contrast
        polylines.add(Polyline(
          points: leg.coordinates,
          color: Colors.black.withValues(alpha: 0.3),
          strokeWidth: leg.isWalk ? 8 : 10,
          pattern: leg.isWalk
              ? StrokePattern.dashed(segments: [12, 8])
              : const StrokePattern.solid(),
        ));
        // Colored route on top
        polylines.add(Polyline(
          points: leg.coordinates,
          color: leg.color,
          strokeWidth: leg.isWalk ? 5 : 7,
          pattern: leg.isWalk
              ? StrokePattern.dashed(segments: [12, 8])
              : const StrokePattern.solid(),
        ));
      }
    }
    return polylines;
  }

  List<Marker> _buildMarkers() {
    final markers = <Marker>[];
    if (_origin != null) {
      markers.add(Marker(
        point: _origin!,
        width: 40,
        height: 40,
        child: GestureDetector(
          onPanEnd: (details) {
            // Simplified drag: we use long-press to reposition
          },
          child: const Icon(Icons.location_on, color: Colors.green, size: 40),
        ),
      ));
    }
    if (_destination != null) {
      markers.add(Marker(
        point: _destination!,
        width: 40,
        height: 40,
        child: const Icon(Icons.location_on, color: Colors.red, size: 40),
      ));
    }
    return markers;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Route Map'),
        actions: [
          if (_origin != null || _destination != null)
            IconButton(
              icon: const Icon(Icons.clear),
              onPressed: () {
                setState(() {
                  _origin = null;
                  _destination = null;
                  _trips = [];
                  _selectedIndex = 0;
                  _statusText = 'Tap map to set origin';
                });
              },
            ),
        ],
      ),
      body: Stack(
        children: [
          FlutterMap(
            mapController: _mapController,
            options: MapOptions(
              initialCenter: const LatLng(defaultLat, defaultLon),
              initialZoom: defaultZoom.toDouble(),
              onTap: _onMapTap,
            ),
            children: [
              TileLayer(
                urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                userAgentPackageName: 'com.stog.stog_app',
              ),
              PolylineLayer(polylines: _buildPolylines()),
              MarkerLayer(markers: _buildMarkers()),
            ],
          ),
          // Status bar
          Positioned(
            top: 8,
            left: 16,
            right: 16,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.92),
                borderRadius: BorderRadius.circular(8),
                boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 4)],
              ),
              child: Row(
                children: [
                  if (_fetching) const SizedBox(
                    width: 16, height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                  if (_fetching) const SizedBox(width: 8),
                  Expanded(child: Text(_statusText, style: const TextStyle(fontWeight: FontWeight.w500))),
                ],
              ),
            ),
          ),
          // Trip cards bottom sheet
          if (_trips.isNotEmpty)
            DraggableScrollableSheet(
              initialChildSize: 0.25,
              minChildSize: 0.08,
              maxChildSize: 0.6,
              builder: (context, scrollController) {
                return Container(
                  decoration: const BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
                    boxShadow: [BoxShadow(color: Colors.black26, blurRadius: 8)],
                  ),
                  child: Column(
                    children: [
                      // Drag handle
                      Container(
                        margin: const EdgeInsets.symmetric(vertical: 8),
                        width: 40,
                        height: 4,
                        decoration: BoxDecoration(
                          color: Colors.grey[300],
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                      Expanded(
                        child: ListView.builder(
                          controller: scrollController,
                          itemCount: _trips.length,
                          itemBuilder: (context, index) {
                            return TripCard(
                              trip: _trips[index],
                              selected: index == _selectedIndex,
                              onTap: () {
                                setState(() { _selectedIndex = index; });
                                _fitBounds();
                              },
                            );
                          },
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
        ],
      ),
    );
  }
}
