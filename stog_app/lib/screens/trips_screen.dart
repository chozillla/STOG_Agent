import 'package:flutter/material.dart';
import '../services/rejseplanen_api.dart';
import '../models/trip.dart';
import '../config.dart';
import '../utils/time_helpers.dart';
import '../utils/colors.dart';
import '../widgets/leg_badge.dart';

class TripsScreen extends StatefulWidget {
  final RejseplanenApi api;
  const TripsScreen({super.key, required this.api});

  @override
  State<TripsScreen> createState() => _TripsScreenState();
}

class _TripsScreenState extends State<TripsScreen> {
  List<TripResult> _trips = [];
  bool _loading = true;
  String? _error;
  String _originName = '';
  String _destName = '';

  @override
  void initState() {
    super.initState();
    _loadTrips();
  }

  Future<void> _loadTrips() async {
    setState(() { _loading = true; _error = null; });
    try {
      final kildedal = await widget.api.locationSearch('Kildedal St.');
      if (kildedal.isEmpty) throw Exception('Could not find Kildedal station');

      var fuglsang = await widget.api.locationSearch('Fuglsang Allé');
      if (fuglsang.isEmpty) fuglsang = await widget.api.locationSearch('Fuglsang Alle');
      if (fuglsang.isEmpty) fuglsang = await widget.api.locationSearch('Fuglsang');
      if (fuglsang.isEmpty) throw Exception('Could not find Fuglsang Allé');

      final origin = kildedal.first;
      final dest = fuglsang.first;

      final rawTrips = await widget.api.searchTrips(
        originId: origin.extId,
        destId: dest.extId,
      );

      setState(() {
        _originName = origin.name;
        _destName = dest.name;
        _trips = processTrips(rawTrips);
        _loading = false;
      });
    } catch (e) {
      setState(() { _error = e.toString(); _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Leave-by Calculator')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!, style: const TextStyle(color: Colors.red)))
              : RefreshIndicator(
                  onRefresh: _loadTrips,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Padding(
                        padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
                        child: Text(
                          '$_originName → $_destName',
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                        child: Text(
                          'Walk: $walkMinutes min · Max wait: $maxStationWait min',
                          style: const TextStyle(fontSize: 12, color: Color(0xFF6C757D)),
                        ),
                      ),
                      Expanded(
                        child: ListView.builder(
                          itemCount: _trips.length,
                          itemBuilder: (context, index) => _buildTripRow(_trips[index]),
                        ),
                      ),
                    ],
                  ),
                ),
    );
  }

  Widget _buildTripRow(TripResult trip) {
    final now = DateTime.now();
    final totalLead = walkMinutes + maxStationWait;
    final depEff = trip.depEffective;
    if (depEff == null) return const SizedBox.shrink();

    final leaveBy = depEff.subtract(Duration(minutes: totalLead));
    final atStation = leaveBy.add(const Duration(minutes: walkMinutes));
    final stationWait = depEff.difference(atStation).inMinutes;
    final minsUntil = leaveBy.difference(now).inMinutes.toDouble();

    final leaveColor = urgencyColor(minsUntil);
    final pastNote = minsUntil < 0 ? ' (past)' : minsUntil < 5 ? ' (!)' : '';

    // Delay info
    String delayText;
    Color delayCol;
    if (trip.cancelled) {
      delayText = 'CANCELLED';
      delayCol = Colors.red;
    } else if (trip.depRealtime == null) {
      delayText = 'no RT';
      delayCol = Colors.grey;
    } else {
      final diff = trip.depRealtime!.difference(trip.depScheduled!).inMinutes;
      if (diff <= 0) {
        delayText = 'on time';
        delayCol = Colors.green;
      } else if (diff <= 3) {
        delayText = '+$diff min';
        delayCol = Colors.orange;
      } else {
        delayText = '+$diff min';
        delayCol = Colors.red;
      }
    }

    // Departure display
    String depDisplay = formatTimeHHMM(trip.depScheduled!);
    if (trip.depRealtime != null && trip.depRealtime != trip.depScheduled) {
      depDisplay += '→${formatTimeHHMM(trip.depRealtime!)}';
    }

    String arrDisplay = formatTimeHHMM(trip.arrScheduled!);
    if (trip.arrRealtime != null && trip.arrRealtime != trip.arrScheduled) {
      arrDisplay += '→${formatTimeHHMM(trip.arrRealtime!)}';
    }

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: leaveColor,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    'Leave ${formatTimeHHMM(leaveBy)}$pastNote',
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 15,
                    ),
                  ),
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: delayCol.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    delayText,
                    style: TextStyle(color: delayCol, fontWeight: FontWeight.w600, fontSize: 12),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                _infoChip('At station', formatTimeHHMM(atStation)),
                const SizedBox(width: 12),
                _infoChip('Depart', depDisplay),
                const SizedBox(width: 12),
                _infoChip('Arrive', arrDisplay),
              ],
            ),
            const SizedBox(height: 6),
            Row(
              children: [
                _infoChip('Wait', '${stationWait}m'),
                const SizedBox(width: 12),
                _infoChip('Duration', trip.durationStr),
                const SizedBox(width: 12),
                _infoChip('Changes', trip.transfers.toString()),
              ],
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 4,
              runSpacing: 4,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                for (int i = 0; i < trip.legs.length; i++) ...[
                  if (i > 0) const Text('→', style: TextStyle(color: Color(0xFFADB5BD), fontSize: 11)),
                  LegBadge(leg: trip.legs[i]),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _infoChip(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 10, color: Color(0xFF6C757D))),
        Text(value, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
      ],
    );
  }
}
