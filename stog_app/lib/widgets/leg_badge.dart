import 'package:flutter/material.dart';
import '../models/trip.dart';

class LegBadge extends StatelessWidget {
  final TripLeg leg;

  const LegBadge({super.key, required this.leg});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
      decoration: BoxDecoration(
        color: leg.isWalk ? const Color(0xFF26A69A) : leg.color,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (leg.isWalk) const Padding(
            padding: EdgeInsets.only(right: 3),
            child: Icon(Icons.directions_walk, color: Colors.white, size: 13),
          ),
          Text(
            leg.name,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 11,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}
