import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'app_localizations.dart';
import 'services/local_db_service.dart';
import 'services/api_service.dart';
import 'services/tflite_service.dart';
import 'screens/login_screen.dart';
import 'screens/home_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final localDb = LocalDbService();
  await localDb.init();

  final tflite = TfliteService();
  await tflite.loadModel(); // no-ops gracefully if crop_grader.tflite isn't present yet

  runApp(UzhavanApp(localDb: localDb, tflite: tflite));
}

class UzhavanApp extends StatelessWidget {
  final LocalDbService localDb;
  final TfliteService tflite;

  const UzhavanApp({super.key, required this.localDb, required this.tflite});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        Provider<LocalDbService>.value(value: localDb),
        Provider<TfliteService>.value(value: tflite),
        Provider<ApiService>(create: (_) => ApiService(localDb)),
      ],
      child: MaterialApp(
        title: 'Uzhavan.AI',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorSchemeSeed: const Color(0xFF2E7D32), // deep green — farm/growth
          useMaterial3: true,
        ),
        supportedLocales: const [
          Locale('ta', ''),
          Locale('en', ''),
        ],
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        home: const _AuthGate(),
      ),
    );
  }
}

/// Minimal auth gate: checks for a stored token and routes accordingly.
/// Kept intentionally simple — swap for a proper AuthProvider + Stream if
/// the app grows session-refresh / multi-account needs.
class _AuthGate extends StatelessWidget {
  const _AuthGate();

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<String?>(
      future: const FlutterSecureStorage().read(key: 'access_token'),
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Scaffold(body: Center(child: CircularProgressIndicator()));
        }
        return snapshot.data != null ? const HomeScreen() : const LoginScreen();
      },
    );
  }
}
