# Uzhavan.AI (உழவன்.AI) × Meta AI

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![Pytest](https://img.shields.io/badge/Tests-29%2F29%20Passing-brightgreen.svg?logo=pytest&logoColor=white)](https://docs.pytest.org)
[![Meta AI](https://img.shields.io/badge/Meta%20AI-5%20Models%20Integrated-0668E1.svg?logo=meta&logoColor=white)](https://dev.meta.ai)
[![Flutter](https://img.shields.io/badge/Flutter-Offline%20First-02569B.svg?logo=flutter&logoColor=white)](https://flutter.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**உழவன் (Uzhavan)** — Tamil for *"Farmer"*.  
**Uzhavan.AI** is an AI-augmented, offline-first agritech platform designed for smallholder farmers in Tamil Nadu, India. It bridges on-device edge computer vision (running offline on low-end Android smartphones) with state-of-the-art Meta AI cloud models to provide transparent crop grading, instant post-harvest decision advisory, algorithmic fair pricing, cooperative logistics pooling, and multi-model quality verification.

---

## Key Documentation Links

- [**NEW_WORK.md**](./NEW_WORK.md) — Comprehensive technical log of every file, service, and test created during integration.
- [**MODELS_USED.md**](./MODELS_USED.md) — Detailed mapping of all 5 Meta models, input/output schemas, and failure fallbacks.
- [**3-Minute Presentation Video**](#3-minute-workflow-video-storyboard) — Full storyboard, visual cues, and voiceover script matching the 1080p demo video.

---

## The Agricultural Challenge

Smallholder farmers across rural Tamil Nadu face severe systemic hurdles:
1. **Middlemen Exploitation**: Intermediaries capture 40–50% of retail consumer price spreads due to asymmetric price information.
2. **Post-Harvest Spoilage**: 30% to 40% of perishable produce (tomatoes, chillies, brinjal, onions) is lost due to delayed sales and lack of storage intelligence.
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
                               │        GET /post-harvest/{id}/explanation ────► Muse Spark 1.3 (Tamil Regex Guardrail)
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
The on-device classification performed by the farmer's smartphone is cryptographically signed with a local UUID and stored locally before any network connection is made.  
**Critical Guarantee:** The device grade is **never overwritten** by cloud audits. Cloud vision evaluations are recorded in an independent audit column to provide transparent buyer assurance without diminishing the farmer's farmgate assessment.

### 2. Strict Numeric Integrity Guardrails (Zero Hallucinations)
Agricultural pricing models cannot tolerate LLM hallucinations. All prices, storage distributions, and revenue calculations are calculated **deterministically in Python**.  
When generating Tamil narrative explanations, `app/services/advisor_explainer.py` extracts all digits using a regex scanner (`_numbers(text)`). If the generated text contains **any number not present in the verified input facts**, the output is discarded immediately (`return None`), guaranteeing that farmers never receive invented market rates.

### 3. Distributed Daily Budget Ceiling
To safeguard against runaway loops or credit depletion, `app/services/meta_ai.py` increments an atomic Redis counter on every call. If requests exceed `META_DAILY_CALL_CAP` (default: 2,000 calls/day), the gateway raises `MetaAIUnavailable`, falling back safely to offline functionality.

---

## 3-Minute Workflow Video Storyboard

A synchronized 1080p Full HD video (`uzhavan_ai_meta_workflow_3min.mp4`) has been compiled for hackathon evaluations and presentations. Each scene runs for exactly 30 seconds:

```
[0:00 - 0:30] Scene 1: Introduction & The Rural Challenge
- Visual: Asymmetric middlemen markups, 30-40% perishability loss, field connectivity gap.
- Script: "Smallholder farmers in Tamil Nadu face severe market exploitation, with up to 40% of
  perishable produce lost post-harvest. Without direct market access or transparent quality grading,
  farmers are forced into distressed sales. Uzhavan.AI combines offline edge AI with Meta Cloud AI."

[0:30 - 1:00] Scene 2: Edge AI & Offline Crop Grading
- Visual: Phone camera viewfinder scanning tomatoes, Softmax confidence bar (Grade A 89%).
- Script: "In rural farmlands, internet connectivity is virtually zero. Our mobile application runs
  a lightweight on-device edge AI model that instantly grades crops like tomatoes, onions, and paddy
  from the camera with zero connectivity. The device establishes an immutable local scan record with
  cryptographic verification."

[1:00 - 1:30] Scene 3: Cloud Sync & Meta Audit
- Visual: Background sync, Spark 1.3 audit, Wonder 1.0 arbitration, SAM 3.1 defect pixel masks.
- Script: "When the farmer reaches a network zone, the app syncs to our FastAPI backend. Here, Meta AI
  takes over to provide buyer trust. Muse Spark 1.3 performs a vision audit on the uploaded photo.
  If Spark disagrees with the phone's offline grade, the heavier Muse Wonder 1.0 is invoked as arbiter.
  We also use SAM 3.1 for defect segmentation."

[1:30 - 2:00] Scene 4: Tamil Voice Intent
- Visual: Audio wave animation, Tamil spoken transcript, structured Pydantic JSON schema extraction.
- Script: "To make the app highly accessible, we replaced complex manual forms with voice. Using Muse
  Voice Transcribe, the farmer simply speaks in Tamil. They can say 'I have 50 kilos of tomatoes to sell.'
  The backend streams this audio, and Muse Spark 1.3 extracts crop, quantity, and district in structured JSON."

[2:00 - 2:30] Scene 5: Autonomous Farm Agent
- Visual: Sell vs Store allocation split, DBSCAN 8km logistics pooling, regex guardrail defense.
- Script: "We also built an autonomous post-harvest advisor. Powered by Muse Spark 1.3’s function-calling,
  this agent dynamically pulls real-time fair market prices, calculates storage vs. sell ratios, and groups
  farmers for logistics pooling. Crucially, strict regex number guardrails prevent any hallucinated prices."

[2:30 - 3:00] Scene 6: Architecture & Conclusion
- Visual: FastAPI + PostgreSQL + Celery + Redis Daily Cap, 29/29 Pytest Passed 100% badge.
- Script: "All of this is supported by a robust backend using Postgres, Celery for asynchronous AI tasks,
  and Redis to enforce strict Meta API daily budget caps. The codebase is fully tested with Pytest and
  100% ready for deployment. Uzhavan.AI bridges edge computing and advanced cloud AI. Thank you."
```

---

## Repository Structure

```text
uzhavan-ai/
├── README.md                   # Primary system documentation & overview
├── NEW_WORK.md                 # Complete hackathon build log & implementation notes
├── MODELS_USED.md              # Detailed Meta AI model specification matrix
├── LICENSE                     # MIT License
├── .gitignore                  # Production Git ignore rules
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
│   └── tests/                  # Pytest test suite (29 tests, 100% passing)
│
├── mobile/                     # Flutter cross-platform mobile client
│   ├── assets/models/          # TFLite INT8 quantized models & label maps
│   ├── assets/lang/            # Tamil (ta.json) & English (en.json) localizations
│   └── lib/                    # Screens (scan, post-harvest, sync, chat) & services
│
└── ai_model/                   # Computer vision model training & TFLite export
    ├── train_yolo.py           # Fine-tuning YOLOv8 classification model
    ├── export_tflite.py        # Quantization & INT8 edge export pipeline
    └── synthetic_augment.py    # Muse Image 1.0 synthetic defect generation
```

---

## Quickstart Guide

### 1. Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- Git
- Docker & Docker Compose (optional for local full-stack run)

### 2. Backend Setup
```bash
# Clone the repository
git clone https://github.com/NivairaaWhite/uzhavan-ai-meta.git
cd uzhavan-ai-meta/backend

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env to add your MODEL_API_KEY from dev.meta.ai
```

### 3. Running the Test Suite
The backend includes a comprehensive 29-test test suite covering auth, offline sync, DBSCAN logistics clustering, post-harvest optimization, and all Meta AI integrations:
```bash
pytest tests/ -v
```
**Result**: `29 passed, 1 warning in 10.84s (100% Pass Rate)`

### 4. Starting the Server
```bash
uvicorn app.main:app --reload --port 8000
```
Interactive OpenAPI documentation will be accessible at:
- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`
- **Health Check**: `http://127.0.0.1:8000/health`

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

This project is licensed under the **MIT License** — see the [LICENSE](./LICENSE) file for details.
