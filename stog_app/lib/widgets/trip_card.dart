import 'package:flutter/material.dart';
import '../models/trip.dart';
import 'leg_badge.dart';

class TripCard extends StatelessWidget {
  final TripResult trip;
  final bool selected;
  final VoidCallback onTap;

  const TripCard({
    super.key,
    required this.trip,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: selected ? const Color(0xFFE8F4FD) : Colors.white,
          border: Border.all(
            color: selected ? const Color(0xFF0074D9) : const Color(0xFFDEE2E6),
            width: 2,
          ),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${trip.departureStr}  →  ${trip.arrivalStr}',
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 4),
            Text(
              '${trip.durationStr}  ·  ${trip.transfers == 0 ? 'Direct' : '${trip.transfers} transfer${trip.transfers > 1 ? 's' : ''}'}',
              style: const TextStyle(fontSize: 13, color: Color(0xFF6C757D)),
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 4,
              runSpacing: 4,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: _buildLegBadges(),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _buildLegBadges() {
    final widgets = <Widget>[];
    for (int i = 0; i < trip.legs.length; i++) {
      if (i > 0) {
        widgets.add(const Text('→', style: TextStyle(color: Color(0xFFADB5BD), fontSize: 11)));
      }
      widgets.add(LegBadge(leg: trip.legs[i]));
    }
    return widgets;
  }
}
