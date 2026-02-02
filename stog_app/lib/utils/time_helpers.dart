DateTime parseApiTime(String date, String time) {
  return DateTime.parse('$date ${time.padRight(8, ':00')}');
}

String formatDuration(int minutes) {
  if (minutes >= 60) {
    return '${minutes ~/ 60}h${(minutes % 60).toString().padLeft(2, '0')}m';
  }
  return '${minutes}m';
}

String formatTimeHHMM(DateTime dt) {
  return '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
}

String formatDelay(DateTime? scheduled, DateTime? realtime) {
  if (realtime == null) return 'no RT';
  final diff = realtime.difference(scheduled!).inMinutes;
  if (diff <= 0) return 'on time';
  return '+$diff min';
}
