# New Work Log — Uzhavan.AI × Meta AI Integration

In accordance with hackathon rules, this document catalogs all code, models, and features built or modified during the event. The baseline repository is preserved in the initial commit.

---

## 1. Edge AI Grader & Classifier Contract (Phase 1)
- **`ai_model/train_yolo.py`**:
  - Converted training pipeline from object detector (`yolov8n.pt`) to ImageFolder classifier (`yolov8n-cls.pt`).
  - Added support for 4 standardized classes: `grade_a`, `grade_b`, `grade_c`, `rejected`.
  - Updated validation metrics to report `top1` accuracy.
- **`ai_model/export_tflite.py`**:
  - Updated export to INT8 quantized TFLite classifier format using `dataset` directory for calibration.
- **`ai_model/data.yaml`**:
  - Removed obsolete detector YAML in favor of ImageFolder directory structure.
- **`mobile/assets/models/labels.txt`**:
  - Updated label set to match backend taxonomy (`grade_a`, `grade_b`, `grade_c`, `rejected`).
- **`mobile/lib/services/tflite_service.dart`**:
  - Added strict tensor shape verification on load (`[1, 224, 224, 3]` -> `[1, 4]`).
  - Implemented graceful fallback when model is absent or mismatched.
- **`mobile/lib/screens/scan_screen.dart`**:
  - Added confidence threshold (< 0.6) prompting user to improve lighting and rescan.

---

## 2. Training Data Generation with Meta AI (Phase 2)
- **`backend/app/ai/rubrics/tomato.md`**:
  - Formal agronomist-style rubric establishing defect criteria and thresholds for Grades A, B, C, and Rejected.
- **`ai_model/synthetic_augment.py`**:
  - Automated augmentation pipeline using `muse-image-1.0` to generate synthetic defect images (`syn_*.jpg`) for rare classes (rot, pest damage).

---

## 3. Server-Side AI Layer & Grade Audit (Phase 3)
- **`backend/app/services/meta_ai.py`**:
  - Central doorway for Meta Model API calls with exponential backoff, circuit-breaker timeout, and Redis-backed daily budget ceiling (`META_DAILY_CALL_CAP`).
  - Implementations for `ask_text()`, `ask_json()` with Pydantic schema validation, and `segment()` for SAM 3.1.
- **`backend/app/services/grade_audit.py`**:
  - `audit_grade()` grading engine evaluating produce against markdown rubrics via `muse-spark-1.3`.
- **`backend/app/tasks.py`**:
  - Added Celery task `audit_listing_grade()`: Audits uploaded photo with `muse-spark-1.3`, automatically escalating to `muse-wonder-1.0` if audit contradicts device grade.
  - Fixed district resolution bug in pooling and fair-price queries (Problems 9 & 10).
- **`backend/app/routers/crops.py`**:
  - Added `POST /crop-listings/{id}/image`: EXIF/GPS scrubbing, resizing to 1024x1024, persistent storage, and background audit queue.
  - Added `GET /crop-listings/{id}/outline`: SAM 3.1 segmentation polygon generator for produce.
- **`backend/app/models.py` & `backend/app/schemas.py`**:
  - Added `image_path`, `audit_status`, `audit_grade`, `audit_confidence`, `audit_defects`, `audit_model`, and `district` to `CropListing`.
  - Added `explanation`, `explanation_lang` to `PostHarvestRecommendation`.
- **`backend/alembic/versions/3d81b94e22a0_meta_ai_audit_and_explainer.py`**:
  - Database migration script adding audit and explanation columns.

---

## 4. Tamil Voice Pipeline & Conversational Advisor (Phase 3 & 4)
- **`backend/app/services/advisor_explainer.py`**:
  - Natural Tamil post-harvest advisory generation from deterministic calculations using `muse-spark-1.3`.
  - Numeric integrity guardrail regex (`_numbers()`) guaranteeing zero hallucinated figures.
- **`backend/app/routers/post_harvest.py`**:
  - Added `GET /post-harvest/{rec_id}/explanation` endpoint.
- **`backend/app/routers/voice.py`**:
  - `POST /voice/intent`: Voice transcript parser extracting harvest parameters (`crop_type`, `quantity_kg`, `district`) with missing field feedback.
  - `POST /voice/speak`: Bhashini text-to-speech audio synthesizer.
  - `WebSocket /voice/stream`: 24 kHz WebSocket streaming relay connecting mobile microphone to `muse-voice-transcribe`.
- **`backend/app/auth.py`**:
  - Added `user_from_token()` for authenticating WebSocket streaming connections.

---

## 5. Autonomous Farm Agent (Phase 3.9)
- **`backend/app/services/farm_agent.py`**:
  - Agentic workflow powered by `muse-spark-1.3` tool calling.
  - Tools: `lookup_fair_price`, `recommend_post_harvest`, `get_scan_audit`, `find_logistics_pool`.
  - Safe bounds: capped at 5 tool calls per execution; answers strictly grounded in tool returns.
- **`backend/app/routers/agent.py`**:
  - Added `POST /agent/ask` exposing agent decisions and tool traces.

---

## 6. Mobile Application Enhancements (Phase 4)
- **`mobile/lib/services/api_service.dart`**:
  - Added methods: `uploadScanImage()`, `parseVoiceIntent()`, `fetchExplanation()`, `askAgent()`.
  - Enhanced `syncQueuedListings()` to return server ID and local image mappings for background upload.
- **`mobile/lib/services/voice_service.dart`**:
  - Configured 24 kHz mono PCM recording.
- **`mobile/lib/models/crop_listing.dart` & `post_harvest_recommendation.dart`**:
  - Updated models with audit fields (`auditStatus`, `auditGrade`, `auditConfidence`) and recommendation `id`.
- **`mobile/lib/screens/results_screen.dart`**:
  - Added AI audit verification badges (Verified, Disagree/Re-scan, Pending).
- **`mobile/lib/screens/sync_screen.dart`**:
  - Added 2G-friendly toggle to selectively upload scan photos for AI audit.
- **`mobile/lib/screens/post_harvest_screen.dart`**:
  - Replaced free-text district input with supported district dropdown.
  - Added voice dictation mic button calling `/voice/intent`.
  - Added Tamil explanation display card above reasoning breakdown.
- **`mobile/assets/lang/ta.json` & `en.json`**:
  - Added localization keys for voice, audit badges, and AI explanations.

---

## 7. Infrastructure & Testing (Phase 0 & 3.8)
- **`backend/docker-compose.yml`**:
  - Added shared `uploads:` volume mounted to both `api` and `celery_worker`.
- **`backend/requirements.txt`**:
  - Added `openai>=1.66`, `Pillow>=10.4`, `websockets>=14.0`.
- **`backend/tests/test_meta_ai.py`**:
  - Full suite of unit tests validating fallback behaviors, hallucination guardrails, audit escalation, and voice intent parsing.
