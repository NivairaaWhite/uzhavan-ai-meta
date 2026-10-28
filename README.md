# Uzhavan.AI (உழவன்.AI) × Meta AI

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![Pytest](https://img.shields.io/badge/Tests-29%20Passing-brightgreen.svg?logo=pytest&logoColor=white)](https://docs.pytest.org)
[![Meta AI](https://img.shields.io/badge/Meta%20AI-5%20Models%20Integrated-0668E1.svg?logo=meta&logoColor=white)](https://dev.meta.ai)
[![Flutter](https://img.shields.io/badge/Flutter-Offline%20First-02569B.svg?logo=flutter&logoColor=white)](https://flutter.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

**உழவன் (Uzhavan)** — Tamil for *"Farmer"*.  
**Uzhavan.AI** is an AI-augmented, offline-first agritech platform designed for smallholder farmers in Tamil Nadu, India. It pairs on-device edge computer vision (running offline on low-end Android smartphones) with state-of-the-art Meta AI cloud models to provide tamper-evident crop grading, instant post-harvest decision advisory, algorithmic fair pricing, cooperative logistics pooling, and multi-model quality verification.

---

## Key Documentation Links

- [**NEW_WORK.md**](./NEW_WORK.md) — Comprehensive technical log of every file, service, and test created during integration.
- [**MODELS_USED.md**](./MODELS_USED.md) — Detailed mapping of all 5 Meta models, input/output schemas, and failure fallbacks.
- [**NOTICE.md**](./NOTICE.md) — Third-party integrations notice (Meta AI, Bhashini, Razorpay, DigiLocker, Agmarknet).
- [**3-Minute Presentation Video Storyboard**](#3-minute-workflow-video-storyboard) — Full storyboard, visual cues, and voiceover script matching the 1080p demo video.

---

## The Agricultural Challenge

Smallholder farmers across rural Tamil Nadu face severe systemic hurdles:
1. **Middlemen Exploitation**: Intermediaries capture significant margins of consumer price spreads due to asymmetric market information.
2. **Post-Harvest Spoilage**: Tomato growers face post-harvest losses of about 10–13% for tomato (NABCONS 2022) due to delayed sales and lack of storage intelligence.
3. **Zero Connectivity in Fields**: Rural farmlands lack cellular connectivity; traditional cloud-only AI solutions fail completely at the farmgate.
4. **Buyer Distrust & Subjective Downgrades**: Buyers frequently dispute crop quality upon delivery, forcing farmers into distressing post-transit discounts.

**Uzhavan.AI solves this by combining local offline edge AI with a verifiable cloud Meta AI audit ledger.**

---

## Architectural Overview

```
PHONE (100% Offline in Field)           BACKEND (FastAPI + Celery + DB)             META AI CLOUD GATEWAY
                                                                                 
Camera ────────────────────────┐                                                 
  │                            │                                                 
  ▼                            │                                                 
TFLite Grader (INT8 Quantized) │                                                 
  │ (Sub-100ms on CPU)         │                                                 
  ▼                            │                                                 
Local SQLite DB ───(Sync)──────┼──────► POST /crop-listings/sync                 
                               │        POST /crop-listings/{id}/image ────────► Muse Spark 1.3 (Vision Quality Audit)
                               │          │                                        │ (Discrepancy escalation)
                               │          ▼                                        ▼
                               │        Celery: audit_listing_grade ───────────► Muse Wonder 1.0 (Arbiter)
                               │        GET /crop-listings/{id}/outline ───────► SAM 3.1 (Defect Pixel Masks)
                               │                                                 
Mic (Tamil Audio) ─────────────┼──────► WS /voice/stream (Relay) ──────────────► Muse Voice Transcribe (Streaming ASR)
                               │          │ (Tamil Transcript)                   
                               │          ▼                                      
                               │        POST /voice/intent ────────────────────► Muse Spark 1.3 (Intent Extraction)
                               │                                                 
Advisor Screen ────────────────┼──────► POST /post-harvest/recommend (Deterministic Math)
                               │          │                                      
                               │          ▼                                      
                               │        GET /post-harvest/{id}/explanation ────► Muse Spark 1.3 (Tamil Guardrail)
                               │                                                 
Conversational Agent ──────────┼──────► POST /agent/chat ──────────────────────► Muse Spark 1.3 (Tool-Calling Agent)
                                                                                  ├── lookup_fair_price()
                                                                                  ├── recommend_post_harvest()
                                                                                  └── get_scan_audit()
```

---

## 5-Tier Meta AI Model Integration

| Model | Purpose | Integration Point | Fallback Behavior |
| :--- | :--- | :--- | :--- |
| **Muse Spark 1.3** | Vision quality audit, Voice intent extraction, Tamil narrative advisory, Tool-calling agent | `/voice/intent`<br>`/post-harvest/{id}/explanation`<br>`/agent/chat` | Falls back to deterministic rules; returns HTTP 503 cleanly when offline. |
| **Muse Wonder 1.0** | Deep agronomic arbitration when edge device grade conflicts with cloud audit | `audit_listing_grade` Celery task | Device grade is preserved; flag marked for human review. |
| **SAM 3.1** | Pixel-level defect segmentation masks (rot, blemish, pest punctures) | `/crop-listings/{id}/outline` | Returns full bounding box without polygon masks. |
| **Muse Voice Transcribe** | Low-latency Tamil speech-to-text WebSocket streaming | `/voice/stream` | Falls back to Bhashini ASR or manual text entry. |
| **Muse Image 1.0** | Synthetic training defect augmentation (`syn_*.jpg`) for rare crop diseases | `ai_model/synthetic_augment.py` | Uses standard geometric data augmentations. |

### Verified Live Model Responses (Tested with Live API)

* **Tamil Post-Harvest Explanation (`muse-spark-1.3`)**:
  > *"தக்காளிகளை மூன்று நாட்கள் வைத்திருக்க குளிர்பதனப் பெட்டியில் வைக்காமல் காம்பு மேல்நோக்கி இருக்குமாறு நிழலான காற்றோட்டமான இடத்தில் பரப்பி வையுங்கள்."*
* **Structured Intent JSON Extraction (`muse-spark-1.3`)**:
  ```json
  {
    "crop_type": "tomato",
    "quantity_kg": 500.0,
    "district": "Coimbatore",
    "missing": []
  }
  ```
* **Impartial Quality Arbitration (`muse-wonder-1.0`)**:
  > *"Verdict: Grade B upheld. 8% blemishes exceed the Grade A tolerance; farmer's claim denied."*

---

## Architectural Invariants & Safety Guardrails

### 1. Device Grade Immutability
The on-device classification performed by the farmer's smartphone is cryptographically signed with a local UUID and stored in SQLite before any network connection is made.  
**Critical Guarantee:** The device grade is **never overwritten** by cloud audits. Cloud vision evaluations are recorded in an independent audit column to provide transparent buyer assurance without diminishing the farmer's farmgate assessment.

### 2. Strict Numeric Integrity Guardrail (No Invented Numbers)
Agricultural pricing models cannot tolerate LLM hallucinations. All prices, storage distributions, and revenue calculations are computed **deterministically in Python**.  
When generating Tamil narrative explanations, `app/services/advisor_explainer.py` extracts all digits using a regex scanner (`_numbers(text)`). If the generated text contains **any number not present in the verified input facts**, the output is discarded immediately (`return None`), ensuring that farmers never receive invented market rates.

### 3. Distributed Daily Budget Ceiling
To safeguard against runaway loops or credit depletion, `app/services/meta_ai.py` increments an atomic Redis counter on every call. If requests exceed `META_DAILY_CALL_CAP` (default: 2,000 calls/day), the gateway raises `MetaAIUnavailable`, falling back safely to offline functionality.

---

## Quickstart

Ensure Docker Desktop is running before launching the multi-container stack.

### 1. One-Command Setup (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/NivairaaWhite/uzhavan-ai-meta.git
cd uzhavan-ai-meta

# 2. Configure environment variables (add MODEL_API_KEY from dev.meta.ai)
cp backend/.env.example backend/.env

# 3. Launch with one command
# On Linux:
./start.sh

# On Windows:
start.bat

# On macOS:
./start.command
```

The launcher starts PostgreSQL (with PostGIS), Redis, FastAPI backend, Celery worker, and Celery beat scheduler. Once booted:
- **Swagger UI**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`

*Note: Meta AI models switch on automatically once `MODEL_API_KEY` is added to `backend/.env`.*

### 2. Manual Backend Run (Without Docker)

```bash
cd backend
python -m venv venv

# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

# Run the test suite
pytest tests/ -v

# Start the development server
uvicorn app.main:app --reload --port 8000
```

### 3. Running the Test Suite
The backend includes a 29-test test suite covering auth, offline sync, DBSCAN logistics clustering, post-harvest optimization, and all Meta AI integrations:
```bash
pytest tests/ -v
```
**Result**: `29 passed across auth, logistics, pricing, Meta AI and post-harvest`


### 4. Running & Testing the Mobile App (Flutter)
Mobile app testers must use their development machine's local IPv4 address instead of `localhost` so the physical device or emulator can communicate with the backend:
```bash
cd mobile

# Pass your local machine's IPv4 address (e.g. http://192.168.1.50:8000)
flutter run --dart-define=API_BASE_URL=http://<IPV4_ADDRESS>:8000
```
*(On the standard Android emulator, `http://10.0.2.2:8000` can also be used to alias the host machine's localhost.)*
---

## 3-Minute Workflow Video Storyboard

A synchronized 1080p Full HD video script matched to the 3-minute video presentation. Each scene runs for exactly 30 seconds:

```
Scene 1 · 0:00–0:30 · Problem and solution
On screen: Problem and solution cards with sourced data.
Voiceover:
"In Tamil Nadu, farmers can lose part of a harvest before it reaches a buyer, and many sell
without knowing a fair price. Fields often have no signal, so cloud-only apps fail exactly
where they are needed. Uzhavan A.I. pairs offline AI on the phone with Meta's cloud models.
The farmer gets a trusted grade, a fair price, and a better way to get produce to market."

Scene 2 · 0:30–1:00 · Offline grading on the phone
On screen: Real app in airplane mode grading a photographed tomato sample, showing softmax output.
Voiceover:
"Out in the field, the app works with no internet. The farmer photographs the crop, and a
lightweight model on the phone grades it as A, B or C, showing how confident it is. The
result is signed and saved on the device straight away. Once recorded, that grade is never
lowered by a buyer or overwritten in the cloud, so the farmer's own assessment cannot be quietly changed."

Scene 3 · 1:00–1:30 · Cloud sync and Meta audit
On screen: Backend log showing sync, Muse Spark audit, Muse Wonder escalation, and real SAM 3.1 mask.
Voiceover:
"When the phone gets a signal, the photo and grade sync to our FastAPI backend, and Meta's
models audit the result. Muse Spark 1.3 checks the photo first. If it disagrees with the
phone, Muse Wonder 1.0 steps in as the arbiter. SAM 3.1 outlines the defects, so buyers can
see exactly what was found. Every verdict is stored next to the farmer's grade, and nothing is erased."

Scene 4 · 1:30–2:00 · Tamil voice
On screen: Real Tamil clip recorded in app, followed by structured JSON.
Voiceover:
"Typing forms is a barrier in the field, so we replaced them with voice. The farmer simply
speaks in Tamil.
[Audio clip: எனக்கு கோயம்புத்தூரில் 500 கிலோ தக்காளி விற்க வேண்டும்.]
That means: I need to sell five hundred kilos of tomatoes in Coimbatore. The backend
transcribes the speech, and Muse Spark turns it into structured data: crop, quantity, district
and action. Anything the farmer did not say is left empty and flagged as missing, never guessed."

Scene 5 · 2:00–2:30 · Post-harvest advisor
On screen: Advisor screen with real numbers, and the log line where an invented number is discarded.
Voiceover:
"The same backend runs a post-harvest advisor. For a batch of tomatoes, it recommends how
much to sell today, how much to hold in storage, and how much, if any, to process, using
current market prices. The backend calculates every rupee amount. The AI only puts those facts
into Tamil, and any number it invents is discarded. Nearby farmers can also be pooled into
shared truckloads to cut freight costs."

Scene 6 · 2:30–3:00 · Stack, tests and close
On screen: pytest ending in '29 passed', GitHub repo page, and closing card.
Voiceover:
"Under the hood: FastAPI, PostgreSQL with PostGIS for location queries, Celery for the heavy
AI jobs, and Redis, which caps daily Meta API usage. Twenty-nine tests pass across auth,
logistics, pricing, the Meta AI integration and the advisor. The code is on GitHub at
NivairaaWhite slash uzhavan-ai-meta. Uzhavan A.I.: edge computing and cloud AI working
together for Indian agriculture. Thank you."
```

---

## Repository Structure

```text
uzhavan-ai/
├── README.md                   # Primary system documentation & overview
├── NEW_WORK.md                 # Complete hackathon build log & implementation notes
├── MODELS_USED.md              # Detailed Meta AI model specification matrix
├── NOTICE.md                   # Third-party integrations notice
├── LICENSE                     # Plain MIT License
├── start.sh                    # Linux one-click launcher (chmod +x)
├── start.bat                   # Windows one-click launcher
├── start.command               # macOS one-click launcher (chmod +x)
├── stop.sh                     # Linux stack teardown (chmod +x)
├── stop.bat                    # Windows stack teardown
├── stop.command                # macOS stack teardown (chmod +x)
│
├── backend/                    # FastAPI, Celery, Postgres, Redis backend
│   ├── app/
│   │   ├── routers/            # crops, voice, agent, post_harvest, users, orders
│   │   ├── services/           # meta_ai, grade_audit, advisor_explainer, farm_agent
│   │   ├── ai/rubrics/         # Produce grading criteria (e.g. tomato.md)
│   │   ├── config.py           # Application settings, secrets, and Meta AI caps
│   │   ├── models.py           # SQLAlchemy domain models (with AI audit columns)
│   │   ├── auth.py             # JWT bearer auth with bcrypt password hashing
│   │   └── tasks.py            # Celery async tasks (grade audit, price scrapers)
│   ├── alembic/                # Database migrations
│   ├── docker-compose.yml      # Multi-container local production stack
│   ├── requirements.txt        # Backend dependencies pinned for reproducibility
│   └── tests/                  # Pytest test suite (29 tests passing)
│
├── mobile/                     # Flutter cross-platform mobile client
│   ├── assets/models/          # TFLite INT8 quantized models & label maps
│   ├── assets/lang/            # Tamil (ta.json) & English (en.json) localizations
│   └── lib/                    # Screens (scan, post-harvest, sync, chat) & services
│
├── ai_model/                   # Computer vision model training & TFLite export
│   ├── train_yolo.py           # Fine-tuning YOLOv8 classification model
│   ├── export_tflite.py        # Quantization & INT8 edge export pipeline
│   └── synthetic_augment.py    # Muse Image 1.0 synthetic defect generation
│
└── tools/                      # Video automation & presentation tools
    ├── presentation.html       # 6-scene 1080p animated HTML presentation with video placeholders
    └── render_video.py         # Playwright + FFmpeg automated 30fps video capture & audio muxer
```

---

## API Reference Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Server health and Meta AI status flag |
| `POST` | `/auth/register` | Farmer & Buyer account registration |
| `POST` | `/auth/login` | OAuth2 password flow, returns JWT access token |
| `POST` | `/crop-listings/sync` | Idempotent bulk sync of offline scan records from mobile |
| `POST` | `/crop-listings/{id}/audit` | Triggers Celery asynchronous vision audit via Muse Spark & Wonder |
| `GET` | `/crop-listings/{id}/outline` | Returns SAM 3.1 pixel defect segmentation masks |
| `POST` | `/voice/intent` | Extracts structured crop/quantity/district JSON from Tamil audio transcript |
| `WS` | `/voice/stream` | WebSocket streaming Tamil speech-to-text relay (Muse Voice Transcribe) |
| `POST` | `/post-harvest/recommend` | Computes optimal deterministic split (Sell vs Cold Store vs Process) |
| `GET` | `/post-harvest/{id}/explanation` | Generates natural Tamil post-harvest advisory via Muse Spark 1.3 |
| `POST` | `/agent/chat` | Autonomous conversational agent orchestrating platform tools |

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](./LICENSE) file for details. Third-party API terms are described in [NOTICE.md](./NOTICE.md).
