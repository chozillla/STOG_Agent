import 'package:flutter/material.dart';
import 'services/rejseplanen_api.dart';
import 'screens/map_screen.dart';
import 'screens/trips_screen.dart';
import 'screens/departures_screen.dart';
import 'screens/search_screen.dart';

void main() {
  runApp(const STOGApp());
}

class STOGApp extends StatelessWidget {
  const STOGApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'S-Tog Commute',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFF0074D9),
        useMaterial3: true,
      ),
      home: const MainShell(),
    );
  }
}

class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _currentIndex = 0;
  final RejseplanenApi _api = RejseplanenApi();

  late final List<Widget> _screens;

  @override
  void initState() {
    super.initState();
    _screens = [
      MapScreen(api: _api),
      TripsScreen(api: _api),
      DeparturesScreen(api: _api),
      SearchScreen(api: _api),
    ];
  }

  @override
  void dispose() {
    _api.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (index) {
          setState(() { _currentIndex = index; });
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.map_outlined),
            selectedIcon: Icon(Icons.map),
            label: 'Map',
          ),
          NavigationDestination(
            icon: Icon(Icons.schedule_outlined),
            selectedIcon: Icon(Icons.schedule),
            label: 'Trips',
          ),
          NavigationDestination(
            icon: Icon(Icons.departure_board_outlined),
            selectedIcon: Icon(Icons.departure_board),
            label: 'Departures',
          ),
          NavigationDestination(
            icon: Icon(Icons.search_outlined),
            selectedIcon: Icon(Icons.search),
            label: 'Search',
          ),
        ],
      ),
    );
  }
}
