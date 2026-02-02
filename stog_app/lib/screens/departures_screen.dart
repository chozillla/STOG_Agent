import 'dart:async';
import 'package:flutter/material.dart';
import '../services/rejseplanen_api.dart';
import '../models/departure.dart';
import '../utils/time_helpers.dart';
import '../utils/colors.dart';

class DeparturesScreen extends StatefulWidget {
  final RejseplanenApi api;
  const DeparturesScreen({super.key, required this.api});

  @override
  State<DeparturesScreen> createState() => _DeparturesScreenState();
}

class _DeparturesScreenState extends State<DeparturesScreen> {
  final _controller = TextEditingController(text: 'Kildedal St.');
  List<Departure> _departures = [];
  String _stationName = '';
  bool _loading = false;
  String? _error;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _fetchDepartures();
    _timer = Timer.periodic(const Duration(seconds: 30), (_) => _fetchDepartures());
  }

  Future<void> _fetchDepartures() async {
    final query = _controller.text.trim();
    if (query.isEmpty) return;
    setState(() { _loading = true; _error = null; });
    try {
      final stops = await widget.api.locationSearch(query);
      if (stops.isEmpty) {
        setState(() { _error = 'Station not found'; _loading = false; });
        return;
      }
      final station = stops.first;
      final deps = await widget.api.getDepartures(station.extId);
      setState(() {
        _stationName = station.name;
        _departures = deps;
        _loading = false;
      });
    } catch (e) {
      setState(() { _error = e.toString(); _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Departures')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: TextField(
              controller: _controller,
              decoration: InputDecoration(
                hintText: 'Station name...',
                suffixIcon: IconButton(
                  icon: const Icon(Icons.search),
                  onPressed: _fetchDepartures,
                ),
                border: const OutlineInputBorder(),
              ),
              onSubmitted: (_) => _fetchDepartures(),
            ),
          ),
          if (_stationName.isNotEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Text(
                'Departures from $_stationName',
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
              ),
            ),
          if (_loading) const Padding(
            padding: EdgeInsets.all(20),
            child: CircularProgressIndicator(),
          ),
          if (_error != null) Padding(
            padding: const EdgeInsets.all(12),
            child: Text(_error!, style: const TextStyle(color: Colors.red)),
          ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _fetchDepartures,
              child: ListView.separated(
                itemCount: _departures.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final dep = _departures[index];
                  final timeStr = formatTimeHHMM(dep.scheduled);
                  final rtStr = dep.realtime != null && dep.realtime != dep.scheduled
                      ? ' → ${formatTimeHHMM(dep.realtime!)}'
                      : '';
                  final delay = dep.delayMinutes;

                  return ListTile(
                    leading: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          '$timeStr$rtStr',
                          style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
                        ),
                      ],
                    ),
                    title: Text(dep.name, style: const TextStyle(fontWeight: FontWeight.w500)),
                    subtitle: Text(dep.direction),
                    trailing: dep.cancelled
                        ? const Chip(
                            label: Text('CANCELLED', style: TextStyle(color: Colors.white, fontSize: 11)),
                            backgroundColor: Colors.red,
                          )
                        : delay > 0
                            ? Chip(
                                label: Text('+$delay min', style: const TextStyle(color: Colors.white, fontSize: 11)),
                                backgroundColor: delayColor(delay),
                              )
                            : dep.realtime != null
                                ? const Chip(
                                    label: Text('on time', style: TextStyle(color: Colors.white, fontSize: 11)),
                                    backgroundColor: Colors.green,
                                  )
                                : null,
                  );
                },
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    _controller.dispose();
    super.dispose();
  }
}
