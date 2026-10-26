# Meta AI Models Used in Uzhavan.AI

This document details every Meta model integrated into Uzhavan.AI during the hackathon, specifying the model identifier, invocation site, inputs, outputs, and fallback behavior when the model or network is unavailable.

| Model ID | File & Function | Input | Output | Fallback Behavior on Failure |
| :--- | :--- | :--- | :--- | :--- |
| **`muse-spark-1.3`** | `backend/app/services/grade_audit.py`<br>`audit_grade()` | Preprocessed produce JPEG (1024x1024 RGB, EXIF stripped) + crop rubric text | `GradeVerdict` JSON schema (`grade`, `confidence`, `defects`, `defect_pct`, `rationale`) | Mark listing `audit_status = 'skipped'`, retain on-device TFLite grade as farmer's source of truth. |
| **`muse-wonder-1.0`** | `backend/app/tasks.py`<br>`audit_listing_grade()` | Produce JPEG + rubric (escalation triggered when `audit_grade != device_grade`) | Deep-reasoning `GradeVerdict` JSON schema arbitrating grade discrepancy | Fall back to Muse Spark's initial verdict; if unavailable, flag for manual admin review. |
| **`sam-3.1`** | `backend/app/services/meta_ai.py`<br>`segment()` | Image JPEG bytes + prompt string (e.g. `"tomato"`, `"bruise"`) | Token stream decoded into polygon masks & bounding boxes | Outline feature omitted in UI; scan grade remains unaffected. |
| **`muse-spark-1.3`** | `backend/app/services/advisor_explainer.py`<br>`explain()` | Deterministic advisory facts JSON (`crop`, `quantities`, `prices`, `channels`) | Warm, concise 3–5 sentence Tamil text explanation for smallholder farmers | Returns `None`; UI cleanly falls back to bullet-point deterministic rule reasoning. |
| **`muse-spark-1.3`** | `backend/app/routers/voice.py`<br>`intent()` | Tamil/English speech transcript string | `HarvestIntent` JSON (`crop_type`, `quantity_kg`, `district`, `missing`) | Returns HTTP 503; UI prompts farmer to use standard dropdown & manual text entry. |
| **`muse-voice-transcribe`** | `backend/app/routers/voice.py`<br>`stream()` (WebSocket relay) | 24 kHz mono 16-bit PCM streaming audio from mobile microphone | Real-time partial & final Tamil transcripts | WebSocket disconnects gracefully; client switches to recorded voice note or manual typing. |
| **`muse-image-1.0`** | `ai_model/synthetic_augment.py`<br>`generate_defect_edits()` | Seed Grade A field photos + natural language defect prompt | Realistic synthetic produce images with defects (`syn_*.jpg`) for rare classes | Training proceeds strictly on existing human-captured photos without synthetic augmentation. |
| **`muse-spark-1.3`** | `backend/app/services/farm_agent.py`<br>`agent_ask()` | Natural language query from farmer in Tamil | Multi-step agent decision trajectory with tool calls (`pricing`, `allocation`, `audit`) | Falls back to direct single-endpoint API recommendation. |

### Architectural Invariants:
1. **Zero-Offline Degradation**: The offline TFLite grader and deterministic post-harvest allocation engine function without any network connectivity.
2. **Deterministic Financial Math**: Prices, allocation splits, and escrow funds are never calculated or altered by generative models. Meta models explain, audit, and orchestrate, but do not price.
3. **Guardrails**:
   - Explanation guardrail enforces strict numeric consistency (`_numbers()` validation ensures no fabricated numbers).
   - Daily budget ceiling (`META_DAILY_CALL_CAP`) prevents unbounded credit exhaustion.
   - Strict privacy stripping: EXIF/GPS and PII are stripped before image or voice data reaches the Meta API.
