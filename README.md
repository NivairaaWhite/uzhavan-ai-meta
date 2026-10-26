# Uzhavan.AI

**உழவன் (Uzhavan)** — Tamil for "farmer." An agritech platform that lets
farmers grade their own crop quality offline on a basic Android phone,
sell into a marketplace at a transparent fair price, get pooled with
nearby farmers to fill a single truck (instead of each hiring separate,
expensive transport), get paid through escrow-protected UPI, and — for
whatever doesn't sell today — get a same-day sell/store/process
recommendation instead of watching it spoil. All without needing
continuous internet access or a middleman.

Built from an uploaded technical blueprint; this repo is the
infrastructure and application code, not a trained AI model — see
"What you still need to do" below for the one piece that genuinely
can't be generated (a labeled crop-image dataset).

## Repo layout

```
backend/     FastAPI + Postgres + Celery — fully working, 25/25 tests passing
mobile/      Flutter app — offline scanning, marketplace, sync, voice
ai_model/    YOLOv8 training + TFLite export pipeline for edge grading
docs/        Architecture decisions and full system requirements
start.bat / start.command / start.sh   one-click backend launcher (Windows/macOS/Linux)
stop.bat / stop.command / stop.sh      stops it again, data preserved
```

Each subfolder has its own README with specifics. Start here for the
whole-system picture.

## One-click start (backend)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/)
(or Docker Engine + Compose on Linux) to already be installed and running —
that's the one prerequisite no script can install for you.

| Platform | Run this | To stop |
|---|---|---|
| Windows | double-click `start.bat` | `stop.bat` |
| macOS | double-click `start.command` (first time: right-click → Open, to clear Gatekeeper) | `stop.command` |
| Linux | `./start.sh` | `./stop.sh` |

What it does: creates `backend/.env` from the example file if it doesn't
exist yet, builds and starts Postgres+PostGIS, Redis, the API, and the
Celery worker/beat via Docker Compose, waits for the API to report
healthy, then opens `http://localhost:8000/docs` in your browser. Your
data persists between stop/start — only `docker compose down -v` (not
what these scripts run) would wipe it.

This starts the **backend** — the deployable server half of the system.
The mobile app is a separate install onto a phone (see below); it isn't
something a desktop "start button" launches.

### Troubleshooting the one-click start

The launcher now checks for and reports on the three problems most likely
to come up on a fresh machine:

**"Docker Desktop is not running"** — the `docker` CLI is on your PATH
but the engine behind it isn't up (common right after a reboot). The
script now detects this, tries to launch Docker Desktop for you on
Windows/macOS, and waits up to two minutes for it to come online before
continuing. On Linux, start the engine with `sudo systemctl start docker`
(or open Docker Desktop for Linux if that's what you have) and re-run the
script.

**Stack starts but never reports healthy** — `start.bat`/`.sh`/`.command`
now run `docker compose up --wait`, scoped to `db redis api celery_worker`
(the services with a real health check), which blocks until all four
pass or fails fast with a clear error instead of guessing with a fixed
timer. `celery_beat` is deliberately left out of that wait: it's a
scheduler with nothing that answers a health-check "ping" the way a
worker does, so it's started normally (and kept alive by
`restart: unless-stopped`) without blocking the rest of the stack on it.
If the wait step fails, the script automatically prints the last lines
of the `api`, `celery_worker`, `celery_beat`, and `db` logs so you can
see the real error immediately, rather than opening a blank browser tab
or watching a "Waiting..." line with no explanation. For the full log
stream, run (from the `backend/` folder):

```bash
docker compose logs -f
```

**A blank page at `localhost:8000/docs`** — this was a symptom of the API
container crashing before ever binding to port 8000, usually because it
tried to reach Postgres before Postgres was truly accepting connections
(a known race with Postgres's own first-run bootstrap process). The fix
was two-layered: `docker-compose.yml`'s database health check now forces
a real TCP probe instead of one that can false-positive during Postgres's
init phase, and the API itself now retries its database connection for
up to a minute at startup instead of crashing on the first attempt —
so a database that comes up a few seconds late is just a log line, not a
dead container.

## Quickstart — backend, manual/no-Docker path

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in real API keys as you get them
pytest tests/ -v               # 25 passed
uvicorn app.main:app --reload  # http://localhost:8000/docs for interactive API
```

## Quickstart — mobile app

```bash
cd mobile
flutter pub get
flutter analyze                # do this first — see mobile/README.md
flutter run --dart-define=API_BASE_URL=http://localhost:8000
```

## What you still need to do

This was built to be a real, running starting point — not a mockup —
but three things need work outside what any code delivery can do:

1. **Register for the external APIs** (Bhashini, Razorpay, DigiLocker —
   see `docs/SYSTEM_REQUIREMENTS.md` for links) and drop the keys into
   `.env`. Every client raises a clear error naming the missing key
   rather than silently faking success.
2. **Collect and label a crop-quality image dataset**, then train the
   grading model — see `ai_model/README.md`. Nothing can substitute for
   this; it's real photos of real produce.
3. **Run `flutter analyze`/`build` yourself** — this environment had no
   Flutter SDK to verify against, so the Dart source is a strong first
   draft, not a guaranteed-clean build. See `mobile/README.md`.

## License

MIT — see `LICENSE`. No warranty is provided; deploying the
payment-escrow and KYC flows against real farmers' money and identity
data is the deploying party's responsibility to compliance-review first.
