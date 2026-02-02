import 'package:flutter_test/flutter_test.dart';
import 'package:stog_app/main.dart';

void main() {
  testWidgets('App renders with 4 navigation tabs', (WidgetTester tester) async {
    await tester.pumpWidget(const STOGApp());
    expect(find.text('Map'), findsOneWidget);
    expect(find.text('Trips'), findsOneWidget);
    expect(find.text('Departures'), findsOneWidget);
    expect(find.text('Search'), findsOneWidget);
  });
}
