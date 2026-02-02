import 'package:flutter/material.dart';

const List<Color> transportColors = [
  Color(0xFF2979FF), // Vivid blue
  Color(0xFFFF6D00), // Vivid orange
  Color(0xFF00C853), // Vivid green
  Color(0xFFFF1744), // Vivid red
  Color(0xFFAA00FF), // Vivid purple
  Color(0xFFFF4081), // Hot pink
  Color(0xFF00BFA5), // Teal
  Color(0xFFFFD600), // Vivid yellow
];

const Color walkColor = Color(0xFF26A69A);       // Teal-green for walking
const Color deselectedColor = Color(0x55999999);  // Semi-transparent gray

Color urgencyColor(double minutesUntil) {
  if (minutesUntil < 0) return Colors.red;
  if (minutesUntil < 5) return Colors.orange;
  return Colors.green;
}

Color delayColor(int delayMinutes) {
  if (delayMinutes <= 0) return Colors.green;
  if (delayMinutes <= 3) return Colors.orange;
  return Colors.red;
}
