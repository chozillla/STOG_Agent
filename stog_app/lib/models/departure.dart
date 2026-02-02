import '../utils/time_helpers.dart';

class Departure {
  final String name;
  final String direction;
  final DateTime scheduled;
  final DateTime? realtime;
  final bool cancelled;

  Departure({
    required this.name,
    required this.direction,
    required this.scheduled,
    this.realtime,
    this.cancelled = false,
  });

  factory Departure.fromJson(Map<String, dynamic> json) {
    final date = json['date'] ?? '';
    final time = json['time'] ?? '';
    final rtDate = json['rtDate'] ?? '';
    final rtTime = json['rtTime'] ?? '';

    return Departure(
      name: (json['name'] ?? '').toString().trim(),
      direction: json['direction'] ?? '',
      scheduled: parseApiTime(date, time),
      realtime: rtTime.isNotEmpty ? parseApiTime(rtDate, rtTime) : null,
      cancelled: json['cancelled'] == true,
    );
  }

  int get delayMinutes {
    if (realtime == null) return 0;
    return realtime!.difference(scheduled).inMinutes;
  }
}
