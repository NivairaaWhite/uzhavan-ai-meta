# Uzhavan.AI — Mobile App (Flutter)

Farmer/student-agent client: offline crop grading, marketplace browsing,
offline-first sync, and Tamil voice input.

## This code was authored, not compiled

This sandbox has no Flutter/Dart SDK and no access to pub.dev, so this
source has been written carefully by hand and sanity-checked (import
coverage, brace balance) but **not run through `flutter analyze` or
`flutter build`**. Do that first on your own machine:

```bash
flutter pub get
flutter analyze
flutter run --dart-define=API_BASE_URL=http://localhost:8000
```

Fix anything the analyzer flags before shipping — treat this as a strong
first draft of every screen and service, not a guaranteed-clean build.

## Structure

```
lib/
  main.dart                  entrypoint, DI via provider
  models/crop_listing.dart   mirrors backend CropListing schema
  services/
    local_db_service.dart    Hive offline queue (source of truth in the field)
    api_service.dart         REST client + bulk sync
    tflite_service.dart      on-device YOLOv8/classifier inference
    voice_service.dart       Bhashini streaming ASR over WebSocket
  screens/
    login_screen.dart
    home_screen.dart
    scan_screen.dart         camera -> on-device grading -> save offline
    results_screen.dart
    marketplace_screen.dart
    sync_screen.dart         manual, visible sync (2G-friendly)
```

## Before this runs end-to-end you still need

1. **A trained `crop_grader.tflite`** in `assets/models/`, from
   `ai_model/` — see that folder's README. Without it, `TfliteService`
   loads safely into a "not ready" state and the app still runs; scanning
   just stays disabled until you drop a real model in.
2. **A running backend** (see `../backend/`) and `API_BASE_URL` pointed
   at it.
3. **A voice pipeline-config proxy route** on the backend if you want
   `voice_service.dart`'s Bhashini key to never touch the device — see
   the note at the top of `lib/services/voice_service.dart`.
4. Real app icons / splash screen / package name (`com.example.uzhavan`
   placeholders in `android/`, `ios/` — not generated here; run
   `flutter create .` in this folder once to scaffold the native
   Android/iOS wrapper projects, since a Dart-only `lib/` isn't a
   buildable app by itself).
5. **i18n wiring**: `assets/lang/{ta,en}.json` and the
   `flutter_localizations`/`intl` dependencies are in place, but no code
   yet loads/switches on them — every string in `lib/screens/` is
   hardcoded English except the login screen's Tamil title. Wire a
   proper `AppLocalizations` (or a simple `Provider<Map<String,String>>`
   loaded from those JSON files) before shipping to Tamil-speaking
   farmers, since that's the primary user base per the blueprint.
