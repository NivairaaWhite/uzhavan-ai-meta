# Uzhavan.AI (உழவன்.AI) × Meta AI

**உழவன் (Uzhavan)** — Tamil for "farmer." An AI-augmented, offline-first agritech platform that empowers smallholder farmers in Tamil Nadu to grade crop quality offline on low-end Android smartphones, receive instant post-harvest decision advice, sell produce at fair transparent prices, pool logistics with neighboring farms, and gain buyer trust via multi-model Meta AI auditing and Tamil voice interaction.

> **Hackathon Documentation Links:**
> - [**NEW_WORK.md**](./NEW_WORK.md) — Comprehensive breakdown of every feature, file, and capability built during the hackathon.
> - [**MODELS_USED.md**](./MODELS_USED.md) — Detailed mapping of all 5 Meta models integrated (Spark 1.3, Wonder 1.0, SAM 3.1, Muse Voice Transcribe, Muse Image 1.0), input/output schemas, and failure fallbacks.

---

## Architecture Overview

```
PHONE (100% Offline Capable)          BACKEND (FastAPI + Celery + DB)               META AI CLOUD
                                                                                 
Camera ────────────────────────┐                                                 
  │                            │                                                 
  ▼                            │                                                 
TFLite Grader (INT8 Quantized) │                                                 
  │ (yolov8n-cls on CPU)       │                                                 
  ▼                            │                                                 
Local Hive DB ────(Sync)───────┼──────► POST /crop-listings/sync                 
                               │        POST /crop-listings/{id}/image ────────► Muse Spark 1.3 (Vision Audit)
                               │          │                                        │ (Disagreement escalation)
                               │          ▼                                        ▼
                               │        Celery: audit_listing_grade ───────────► Muse Wonder 1.0 (Arbiter)
                               │        GET /crop-listings/{id}/outline ───────► SAM 3.1 (Produce Masks)
                               │                                                 
Mic (24 kHz PCM) ──────────────┼──────► WS /voice/stream (Relay) ──────────────► Muse Voice Transcribe (Tamil ASR)
                               │          │ (Transcript)                         
                               │          ▼                                      
                               │        POST /voice/intent ────────────────────► Muse Spark 1.3 (Harvest Intent)
                               │                                                 
Advisor Screen ────────────────┼──────► POST /post-harvest/recommend (Deterministic)
                               │          │                                      
                               │          ▼                                      
                               │        GET /post-harvest/{id}/explanation ────► Muse Spark 1.3 (Tamil Guardrail)
                               │                                                 
Conversational Agent ──────────┼──────► POST /agent/ask ───────────────────────► Muse Spark 1.3 (Function Calling)
                                                                                   │ ├─ lookup_fair_price
                                                                                   │ ├─ recommend_post_harvest
                                                                                   │ └─ get_scan_audit
```

---

## Key Highlights

1. **Edge AI Stays Offline**: The on-device classifier (`crop_grader.tflite`) runs in airplane mode with sub-200ms latency on 2GB RAM phones. Meta models do not replace this core promise; they elevate it.
2. **Server-Side AI Grade Audit & Arbitration**: When scans sync online, `muse-spark-1.3` audits produce photos against agronomist rubrics. If the audit disagrees with the farmer's edge grade, `muse-wonder-1.0` is invoked as a deep-reasoning arbiter. The farmer's on-device record is never overwritten.
3. **Natural Tamil Post-Harvest Explanations**: Converts complex sell/store/process mathematical allocations into simple, encouraging Tamil advice for smallholder farmers. Guarded by a strict regex numeric verifier that catches and rejects hallucinated prices.
4. **Autonomous Farm Agent**: An agentic endpoint powered by `muse-spark-1.3` function-calling that orchestrates deterministic backend tools (pricing, post-harvest allocation, logistics clustering, audit history) to answer multi-turn Tamil queries.
5. **Synthetic Defect Augmentation**: Overcomes dataset scarcity using `muse-image-1.0` to generate realistic synthetic defects (`syn_*.jpg`) for rare classes like rot and pest damage while preserving authentic background lighting and crates.
6. **Robust Guardrails**: Zero-hallucination number checks, distributed Redis budget ceilings (`META_DAILY_CALL_CAP`), and automated fallback so that the entire platform functions smoothly even if cloud AI is toggled off.

---

## Repository Structure

```
uzhavan-ai/
├── NEW_WORK.md                 # Complete record of hackathon build
├── MODELS_USED.md              # Meta AI model integration matrix
├── .gitignore                  # Production Git ignore
├── backend/                    # FastAPI, Celery, Postgres, Redis backend
│   ├── app/
│   │   ├── ai/rubrics/         # Produce grading rubrics (e.g. tomato.md)
│   │   ├── routers/            # crops, voice, agent, post-harvest, orders, etc.
│   │   ├── services/           # meta_ai, grade_audit, advisor_explainer, farm_agent
│   │   ├── config.py           # Meta AI settings & budget caps
│   │   ├── models.py           # Schema with AI audit columns & district fixes
│   │   └── tasks.py            # Celery tasks (audit, price scraping, pooling)
│   ├── alembic/                # Database migrations (including meta_ai revision)
│   ├── docker-compose.yml      # Containerized stack with shared uploads volume
│   └── tests/                  # Pytest test suite with Meta AI unit tests
├── mobile/                     # Flutter cross-platform mobile client
│   ├── assets/models/          # TFLite labels and INT8 quantized model assets
│   ├── assets/lang/            # Tamil (ta.json) & English (en.json) localizations
│   └── lib/                    # Screens (scan, post-harvest, sync, results) & services
└── ai_model/                   # YOLOv8 classification & TFLite export pipeline
    ├── train_yolo.py           # Classifier fine-tuning (yolov8n-cls.pt)
    ├── export_tflite.py        # Quantized INT8 TFLite exporter
    └── synthetic_augment.py    # Muse Image 1.0 defect generation tool
```

---

## Quickstart

### 1. One-Click Backend Launcher (Docker)
Ensure Docker Desktop is running:
- **Windows**: Double-click `start.bat`
- **Linux**: Run `./start.sh`
- **macOS**: Double-click `start.command`

The backend will boot PostgreSQL (with PostGIS), Redis, FastAPI API server, Celery worker, and Celery beat scheduler. Visit `http://localhost:8000/docs` to test endpoints interactively.

### 2. Manual Backend Run (No Docker)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Add your MODEL_API_KEY from dev.meta.ai
pytest tests/ -v
uvicorn app.main:app --reload --port 8000
```

### 3. Mobile App (Flutter)
```bash
cd mobile
flutter pub get
flutter run --dart-define=API_BASE_URL=http://localhost:8000
```

---

## 3-Minute Demo Video Walkthrough
1. **Offline Edge Grading**: Switch phone to Airplane mode. Point camera at produce crate. Tap "Capture & Grade". On-device TFLite grades within 150 ms and saves locally to Hive.
2. **Network Reconnection & Audit**: Disable Airplane mode. Navigate to "Sync". Sync uploaded batch with produce image. Server Celery worker processes `muse-spark-1.3` audit and attaches verified badge.
3. **Tamil Voice Input**: In "Post-Harvest Advisor", tap the microphone button. Speak a harvest sentence in Tamil. Voice intent parser extracts crop, quantity, and district.
4. **Post-Harvest Decision & AI Explanation**: View deterministic optimal split (sell today / cold store / processing) with natural Tamil narrative explanation generated by Muse Spark.
5. **Autonomous Farm Agent**: Pose an advisory question to the agent. Watch the tool execution trace resolve fair market prices and routing in real time.

---

## License
MIT License. See `LICENSE` for details.
