# System Requirements

Consolidated from the original blueprint, adjusted to match what's
actually implemented in this repo (e.g. PostGIS is optional at MVP
scale — see ARCHITECTURE.md — so it's marked as such below).

## 1. Backend server (required to run anything beyond mobile-only offline scanning)

| Resource | Minimum | Recommended (production) |
|---|---|---|
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 GB | 8 GB |
| Disk | 20 GB SSD | 50+ GB SSD (grows with scan-image storage) |
| Network | Public IPv4, ports 80/443 open | + a domain name for TLS |

Runs as Docker Compose services: `api`, `db` (Postgres 16 + PostGIS
extension — extension is present but only required if you adopt the
`ST_ClusterDBSCAN` scaling path in ARCHITECTURE.md), `redis`,
`celery_worker`, `celery_beat`. A $6–12/mo droplet (DigitalOcean,
Hetzner) or AWS `t3.medium` covers the minimum tier comfortably.

## 2. Developer machine (to build/modify either the backend or the app)

| Tool | Version |
|---|---|
| Python | 3.11+ |
| Docker + Docker Compose | current stable |
| Flutter SDK | 3.24+ (Dart 3.3+) — **not installed in this delivery's build environment; install locally before running the mobile app** |
| Android Studio or Xcode | for building/signing the mobile app |
| Git | any recent version |

## 3. Mobile client (farmer / student-agent phone)

Unchanged from the original blueprint — these are real constraints for
rural Tamil Nadu deployment, not arbitrary:

- Android 8.0 (API 26)+
- 2 GB RAM minimum, 3–4 GB recommended
- Rear camera, 8MP+, autofocus, flash
- Must function with zero connectivity for scanning; syncs over
  2G/3G/4G/Wi-Fi when available (this is what `LocalDbService` +
  `SyncScreen` in the Flutter app implement)

## 4. AI model training (one-time / periodic, not part of the production server)

| Resource | Minimum |
|---|---|
| GPU | NVIDIA T4 or better (Colab/Kaggle free tier, or AWS `g4dn.xlarge`) |
| Storage | Depends on dataset size — budget 10–50 GB for a few thousand labeled images |
| Framework | PyTorch + Ultralytics (see `ai_model/requirements.txt`) |

This is **not** a always-on production requirement — you train
periodically as you collect more labeled data, export a new
`crop_grader.tflite`, and ship it in the next app release. The phone
never trains anything; it only runs inference.

## 5. Accounts / API keys needed before the integrations in `app/services/` do anything live

| Service | Where to register | Used for |
|---|---|---|
| Bhashini | https://bhashini.gov.in | Tamil voice ASR/TTS/translation |
| Razorpay | https://dashboard.razorpay.com (start on test keys) | UPI collection, escrow-style Route transfers, IMPS payout |
| DigiLocker | https://partners.digilocker.gov.in | e-KYC without storing raw ID documents |
| data.gov.in (OGD India), optional | https://data.gov.in | Stable JSON feed for Agmarknet prices, instead of HTML scraping |
| Google Maps, optional | https://console.cloud.google.com | Alternative to OSRM for route distance/duration |

Every one of these is wired as a real client in `backend/app/services/`
and fails loudly (a clear exception, not silent fake data) if its keys
are missing — see each file's docstring.
