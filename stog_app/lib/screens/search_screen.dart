import 'package:flutter/material.dart';
import '../services/rejseplanen_api.dart';
import '../models/stop_location.dart';

class SearchScreen extends StatefulWidget {
  final RejseplanenApi api;
  const SearchScreen({super.key, required this.api});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final _controller = TextEditingController();
  List<StopLocation> _results = [];
  bool _loading = false;
  String? _error;

  Future<void> _search() async {
    final query = _controller.text.trim();
    if (query.isEmpty) return;
    setState(() { _loading = true; _error = null; });
    try {
      final results = await widget.api.locationSearch(query);
      setState(() { _results = results; _loading = false; });
    } catch (e) {
      setState(() { _error = e.toString(); _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Station Search')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: TextField(
              controller: _controller,
              decoration: InputDecoration(
                hintText: 'Search station name...',
                suffixIcon: IconButton(
                  icon: const Icon(Icons.search),
                  onPressed: _search,
                ),
                border: const OutlineInputBorder(),
              ),
              onSubmitted: (_) => _search(),
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
            child: ListView.separated(
              itemCount: _results.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final stop = _results[index];
                return ListTile(
                  leading: const Icon(Icons.train, color: Color(0xFF0074D9)),
                  title: Text(stop.name),
                  subtitle: Text(
                    'ID: ${stop.extId}\nCoords: ${stop.lat.toStringAsFixed(4)}, ${stop.lon.toStringAsFixed(4)}',
                  ),
                  isThreeLine: true,
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
}
