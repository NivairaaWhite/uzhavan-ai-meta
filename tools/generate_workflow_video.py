"""
Uzhavan.AI × Meta AI: 3-Minute Presentation Video Generator
Generates a synchronized 1080p 60fps/10fps MP4 video matching the evaluation storyboard.
"""
import math
import os
import subprocess
import sys

try:
    import imageio_ffmpeg
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Please install Pillow, imageio, and imageio-ffmpeg: pip install Pillow imageio imageio-ffmpeg")
    sys.exit(1)

WIDTH = 1920
HEIGHT = 1080
FPS = 10
TOTAL_SECONDS = 180
TOTAL_FRAMES = FPS * TOTAL_SECONDS  # 1800 frames
SCENE_DURATION = 30  # seconds per scene
FRAMES_PER_SCENE = FPS * SCENE_DURATION

OUTPUT_PATH = os.path.join(os.path.expanduser("~"), "Downloads", "uzhavan_ai_meta_workflow_3min.mp4")

font_brand = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 36)
font_scene_title = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 26)
font_timer = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 24)
font_h1 = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 32)
font_h2 = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 24)
font_body = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 20)
font_bold = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 20)
font_code = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 20)
font_prompt_title = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 22)
font_prompt = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 20)

try:
    font_tamil = ImageFont.truetype(r"C:\Windows\Fonts\Nirmala.ttc", 26)
except Exception:
    font_tamil = font_body

SCRIPTS = [
    (
        "SCENE 1: INTRODUCTION & THE RURAL CHALLENGE",
        "\"Smallholder farmers in Tamil Nadu face severe market exploitation, with up to 40% of perishable produce lost post-harvest.\n"
        "Without direct market access or transparent quality grading, farmers are forced into distressed sales. Uzhavan.AI combines offline edge AI with Meta Cloud AI.\""
    ),
    (
        "SCENE 2: EDGE AI & OFFLINE CROP GRADING",
        "\"In rural farmlands, internet connectivity is virtually zero. Our mobile application runs a lightweight on-device edge AI model that instantly\n"
        "grades crops like tomatoes, onions, and paddy from the camera with zero connectivity. The device establishes an immutable local scan record with cryptographic verification.\""
    ),
    (
        "SCENE 3: CLOUD SYNC & META AUDIT",
        "\"When the farmer reaches a network zone, the app syncs to our FastAPI backend. Here, Meta AI takes over to provide buyer trust.\n"
        "Muse Spark 1.3 performs a vision audit on the uploaded photo. If Spark disagrees with the phone's offline grade, the heavier Muse Wonder 1.0 is invoked as arbiter. We also use SAM 3.1 for defect segmentation.\""
    ),
    (
        "SCENE 4: TAMIL VOICE INTENT",
        "\"To make the app highly accessible, we replaced complex manual forms with voice. Using Muse Voice Transcribe, the farmer simply speaks in Tamil.\n"
        "They can say 'I have 50 kilos of tomatoes to sell.' The backend streams this audio, and Muse Spark 1.3 extracts crop, quantity, and district in structured JSON.\""
    ),
    (
        "SCENE 5: AUTONOMOUS FARM AGENT",
        "\"We also built an autonomous post-harvest advisor. Powered by Muse Spark 1.3’s function-calling, this agent dynamically pulls real-time fair market prices,\n"
        "calculates storage vs. sell ratios, and groups farmers for logistics pooling. Crucially, strict regex number guardrails prevent any hallucinated prices.\""
    ),
    (
        "SCENE 6: ARCHITECTURE & CONCLUSION",
        "\"All of this is supported by a robust backend using Postgres, Celery for asynchronous AI tasks, and Redis to enforce strict Meta API daily budget caps.\n"
        "The codebase is fully tested with Pytest and 100% ready for deployment. Uzhavan.AI bridges edge computing and advanced cloud AI. Thank you.\""
    )
]

def draw_header_and_footer(draw, frame_idx):
    current_sec = frame_idx / FPS
    scene_idx = min(int(current_sec // SCENE_DURATION), 5)
    scene_title, script_text = SCRIPTS[scene_idx]

    draw.rectangle([(0, 0), (WIDTH, 75)], fill=(15, 23, 42))
    draw.text((40, 18), "UZHAVAN.AI", font=font_brand, fill=(16, 185, 129))
    draw.text((275, 24), "x", font=font_scene_title, fill=(156, 163, 175))
    draw.text((305, 18), "META AI", font=font_brand, fill=(6, 182, 212))

    pill_w = 640
    pill_x = (WIDTH - pill_w) // 2
    draw.rounded_rectangle([(pill_x, 15), (pill_x + pill_w, 60)], radius=8, fill=(30, 41, 59), outline=(51, 65, 85), width=2)
    draw.text((pill_x + 25, 22), scene_title, font=font_scene_title, fill=(241, 245, 249))

    mins = int(current_sec // 60)
    secs = int(current_sec % 60)
    timer_str = f"[{mins:02d}:{secs:02d} / 03:00]"
    draw.text((WIDTH - 260, 25), timer_str, font=font_timer, fill=(203, 213, 225))

    draw.rectangle([(0, 72), (WIDTH, 76)], fill=(30, 41, 59))
    prog_w = int((current_sec / TOTAL_SECONDS) * WIDTH)
    draw.rectangle([(0, 72), (prog_w, 76)], fill=(16, 185, 129))

    draw.rectangle([(0, HEIGHT - 145), (WIDTH, HEIGHT)], fill=(15, 23, 42), outline=(51, 65, 85), width=2)
    draw.text((40, HEIGHT - 135), f">> YOUR SPOKEN VOICEOVER SCRIPT [{scene_idx*30:02d}s - {(scene_idx+1)*30:02d}s]:", font=font_prompt_title, fill=(245, 158, 11))
    draw.text((40, HEIGHT - 100), script_text, font=font_prompt, fill=(226, 232, 240))

def render_scene_1(draw, progress):
    draw.rounded_rectangle([(80, 110), (920, 890)], radius=12, fill=(24, 32, 47), outline=(51, 65, 85), width=2)
    draw.text((120, 140), "The Rural Challenge in Tamil Nadu", font=font_h1, fill=(239, 68, 68))
    problems = [
        ("Exploitative Middlemen", "Farmers receive only 20-30% of final retail consumer value."),
        ("Post-Harvest Spoilage", "30% to 40% of perishable tomatoes and onions rot in transit."),
        ("Information Asymmetry", "Farmers cannot access fair Mandi market rates at harvest time."),
        ("Zero Field Connectivity", "Field farms lack cellular data - cloud-only solutions fail.")
    ]
    y = 220
    for title, desc in problems:
        draw.ellipse([(120, y + 6), (134, y + 20)], fill=(239, 68, 68))
        draw.text((150, y), title, font=font_h2, fill=(248, 250, 252))
        draw.text((150, y + 34), desc, font=font_body, fill=(148, 163, 184))
        y += 105

    draw.rounded_rectangle([(980, 110), (1840, 890)], radius=12, fill=(24, 32, 47), outline=(51, 65, 85), width=2)
    draw.text((1020, 140), "The Uzhavan.AI x Meta AI Solution", font=font_h1, fill=(16, 185, 129))
    solutions = [
        ("On-Device Offline Edge AI", "Instant computer vision crop grading on the phone without internet."),
        ("Meta AI Cloud Verification", "Multi-model audit: Spark 1.3, Wonder 1.0, and SAM 3.1 build buyer trust."),
        ("Zero-Barrier Tamil Voice", "Farmers report harvest volume naturally using Tamil speech intent."),
        ("Fair Price & Pooled Logistics", "Algorithmic fair pricing and geo-pooling save 45% on transport.")
    ]
    y = 220
    for title, desc in solutions:
        draw.ellipse([(1020, y + 6), (1034, y + 20)], fill=(16, 185, 129))
        draw.text((1050, y), title, font=font_h2, fill=(248, 250, 252))
        draw.text((1050, y + 34), desc, font=font_body, fill=(148, 163, 184))
        y += 105

    draw.rounded_rectangle([(1020, 770), (1240, 850)], radius=8, fill=(30, 41, 59))
    draw.text((1045, 785), "-40% Spoilage", font=font_bold, fill=(16, 185, 129))
    draw.text((1040, 815), "Post-harvest loss", font=font_body, fill=(148, 163, 184))

    draw.rounded_rectangle([(1280, 770), (1520, 850)], radius=8, fill=(30, 41, 59))
    draw.text((1305, 785), "+65% Spread Share", font=font_bold, fill=(6, 182, 212))
    draw.text((1300, 815), "Passed directly to farmer", font=font_body, fill=(148, 163, 184))

    draw.rounded_rectangle([(1560, 770), (1800, 850)], radius=8, fill=(30, 41, 59))
    draw.text((1585, 785), "100% Offline Ready", font=font_bold, fill=(245, 158, 11))
    draw.text((1580, 815), "Farmgate execution", font=font_body, fill=(148, 163, 184))

def render_scene_2(draw, progress):
    draw.rounded_rectangle([(80, 110), (920, 890)], radius=12, fill=(24, 32, 47), outline=(51, 65, 85), width=2)
    draw.text((120, 140), "Edge Mobile Computer Vision", font=font_h1, fill=(59, 130, 246))
    draw.rounded_rectangle([(200, 220), (800, 780)], radius=24, fill=(15, 23, 42), outline=(71, 85, 105), width=3)
    draw.rounded_rectangle([(230, 260), (770, 680)], radius=12, fill=(11, 15, 25), outline=(16, 185, 129), width=2)
    c_len = 30
    draw.line([(250, 280), (250 + c_len, 280)], fill=(16, 185, 129), width=4)
    draw.line([(250, 280), (250, 280 + c_len)], fill=(16, 185, 129), width=4)
    draw.line([(750, 280), (750 - c_len, 280)], fill=(16, 185, 129), width=4)
    draw.line([(750, 280), (750, 280 + c_len)], fill=(16, 185, 129), width=4)
    draw.line([(250, 660), (250 + c_len, 660)], fill=(16, 185, 129), width=4)
    draw.line([(250, 660), (250, 660 - c_len)], fill=(16, 185, 129), width=4)
    draw.line([(750, 660), (750 - c_len, 660)], fill=(16, 185, 129), width=4)
    draw.line([(750, 660), (750, 660 - c_len)], fill=(16, 185, 129), width=4)
    draw.rounded_rectangle([(320, 300), (680, 345)], radius=6, fill=(30, 41, 59))
    draw.text((340, 310), "Scanning Tomato Batch (500kg)", font=font_bold, fill=(241, 245, 249))
    draw.ellipse([(420, 410), (580, 570)], fill=(220, 38, 38))
    draw.text((455, 475), "Crop Detected", font=font_bold, fill=(255, 255, 255))
    draw.rounded_rectangle([(300, 710), (700, 755)], radius=6, fill=(16, 185, 129))
    draw.text((330, 722), "* OFFLINE MODE: 42ms Inference *", font=font_bold, fill=(15, 23, 42))

    draw.rounded_rectangle([(980, 110), (1840, 890)], radius=12, fill=(24, 32, 47), outline=(51, 65, 85), width=2)
    draw.text((1020, 140), "Edge Softmax Quality Assessment", font=font_h1, fill=(16, 185, 129))
    draw.text((1020, 210), "On-Device Neural Network Output:", font=font_h2, fill=(203, 213, 225))
    draw.text((1020, 270), "Grade A (Premium - Firm, uniform color, zero rot)", font=font_bold, fill=(248, 250, 252))
    draw.rounded_rectangle([(1020, 305), (1750, 345)], radius=6, fill=(30, 41, 59))
    draw.rounded_rectangle([(1020, 305), (1020 + int(730 * 0.89), 345)], radius=6, fill=(16, 185, 129))
    draw.text((1680, 312), "89.2%", font=font_bold, fill=(255, 255, 255))

    draw.text((1020, 380), "Grade B (Minor skin blemishes, market viable)", font=font_bold, fill=(248, 250, 252))
    draw.rounded_rectangle([(1020, 415), (1750, 455)], radius=6, fill=(30, 41, 59))
    draw.rounded_rectangle([(1020, 415), (1020 + int(730 * 0.088), 455)], radius=6, fill=(245, 158, 11))
    draw.text((1680, 422), "8.8%", font=font_bold, fill=(255, 255, 255))

    draw.text((1020, 490), "Grade C / Rejected (Soft spots, overripe)", font=font_bold, fill=(248, 250, 252))
    draw.rounded_rectangle([(1020, 525), (1750, 565)], radius=6, fill=(30, 41, 59))
    draw.rounded_rectangle([(1020, 525), (1020 + int(730 * 0.02), 565)], radius=6, fill=(239, 68, 68))
    draw.text((1680, 532), "2.0%", font=font_bold, fill=(255, 255, 255))

    draw.rounded_rectangle([(1020, 630), (1800, 830)], radius=8, fill=(15, 23, 42), outline=(16, 185, 129), width=2)
    draw.text((1050, 655), "CORE INVARIANT: DEVICE GRADE IMMUTABILITY", font=font_h2, fill=(16, 185, 129))
    invariants = [
        "- Scan record is digitally signed with local offline UUID: 8e4c19...4b",
        "- Stored in SQLite device database prior to any network connection",
        "- Device grade is NEVER downgraded by buyers or overwritten on cloud",
        "- Establishes uncompromised farmer trust at the point of harvest"
    ]
    y_inv = 700
    for line in invariants:
        draw.text((1050, y_inv), line, font=font_body, fill=(203, 213, 225))
        y_inv += 30

def render_scene_3(draw, progress):
    draw.rounded_rectangle([(80, 110), (920, 890)], radius=12, fill=(24, 32, 47), outline=(51, 65, 85), width=2)
    draw.text((120, 140), "Cloud Sync & Meta AI Audit", font=font_h1, fill=(6, 182, 212))
    steps = [
        ("1. Fast Background Sync", "When device regains network, photo & edge grade sync to FastAPI.", (59, 130, 246)),
        ("2. Muse Spark 1.3 Vision Audit", "Fast visual audit runs on server to confirm edge crop grade.", (16, 185, 129)),
        ("3. Discrepancy Escalation", "If Spark disagrees with edge device, Muse Wonder 1.0 is called.", (245, 158, 11)),
        ("4. Muse Wonder 1.0 Arbiter", "Deep agronomic reasoning model acts as neutral arbitrator.", (168, 85, 247))
    ]
    y = 220
    for title, desc, col in steps:
        draw.rounded_rectangle([(120, y), (880, y + 80)], radius=8, fill=(15, 23, 42), outline=col, width=2)
        draw.text((140, y + 12), title, font=font_bold, fill=col)
        draw.text((140, y + 42), desc, font=font_body, fill=(203, 213, 225))
        y += 105

    draw.rounded_rectangle([(120, 680), (880, 830)], radius=8, fill=(30, 41, 59))
    draw.text((140, 705), "Audit Rule: Device Grade is Invariant", font=font_bold, fill=(255, 255, 255))
    draw.text((140, 745), "Server audits are recorded alongside device grades in a permanent\nverified ledger. The farmer's field assessment cannot be wiped out.", font=font_body, fill=(148, 163, 184))

    draw.rounded_rectangle([(980, 110), (1840, 890)], radius=12, fill=(24, 32, 47), outline=(51, 65, 85), width=2)
    draw.text((1020, 140), "SAM 3.1 Defect Pixel Segmentation", font=font_h1, fill=(16, 185, 129))
    draw.text((1020, 205), "Prompt Concept: 'rot and skin blemishes'", font=font_h2, fill=(203, 213, 225))
    draw.rounded_rectangle([(1020, 250), (1800, 620)], radius=12, fill=(15, 23, 42), outline=(71, 85, 105), width=2)
    draw.ellipse([(1180, 310), (1460, 560)], fill=(220, 38, 38))
    draw.polygon([(1350, 400), (1420, 430), (1400, 480), (1330, 450)], fill=(16, 185, 129, 180), outline=(52, 211, 153))
    draw.text((1440, 420), "<-- SAM 3.1 Pixel Mask", font=font_code, fill=(52, 211, 153))
    draw.text((1440, 450), "    Defect Ratio: 7.8%", font=font_code, fill=(203, 213, 225))
    draw.rounded_rectangle([(1060, 530), (1400, 590)], radius=6, fill=(30, 41, 59))
    draw.text((1080, 545), "Target: Blemish / Sun Scald", font=font_bold, fill=(241, 245, 249))

    draw.rounded_rectangle([(1020, 660), (1800, 840)], radius=8, fill=(15, 23, 42), outline=(168, 85, 247), width=2)
    draw.text((1050, 680), "LIVE ARBITRATION VERDICT (Wonder 1.0):", font=font_bold, fill=(168, 85, 247))
    draw.text((1050, 715), "\"Grade B upheld. Defect coverage measured by SAM is 7.8%,", font=font_code, fill=(248, 250, 252))
    draw.text((1050, 745), " which is within Grade B threshold (5-10%). Blemishes are superficial", font=font_code, fill=(248, 250, 252))
    draw.text((1050, 775), " skin-deep with no fungal rot. Product is safe for 7-day transport.\"", font=font_code, fill=(52, 211, 153))

def render_scene_4(draw, progress):
    draw.rounded_rectangle([(80, 110), (920, 890)], radius=12, fill=(24, 32, 47), outline=(51, 65, 85), width=2)
    draw.text((120, 140), "Zero-Barrier Voice Interface", font=font_h1, fill=(59, 130, 246))
    draw.text((120, 195), "Muse Voice Transcribe (Real-Time Tamil Audio)", font=font_body, fill=(148, 163, 184))

    draw.rounded_rectangle([(120, 240), (880, 440)], radius=12, fill=(15, 23, 42), outline=(59, 130, 246), width=2)
    draw.text((150, 260), "Streaming Audio Input (Tamil):", font=font_bold, fill=(203, 213, 225))
    
    wave_x = 160
    for i in range(28):
        h = max(6, int(abs(35 * math.sin(progress * 15 + i * 0.6))))
        draw.rounded_rectangle([(wave_x, 350 - h), (wave_x + 14, 350 + h)], radius=3, fill=(59, 130, 246))
        wave_x += 25

    draw.rounded_rectangle([(120, 480), (880, 630)], radius=12, fill=(30, 41, 59), outline=(16, 185, 129), width=2)
    draw.text((150, 500), "Spoken Farmer Transcript (Tamil):", font=font_bold, fill=(16, 185, 129))
    draw.text((150, 540), "எனக்கு கோயம்புத்தூரில் 500 கிலோ தக்காளி விற்க வேண்டும்", font=font_tamil, fill=(255, 255, 255))
    draw.text((150, 585), "Translation: 'I need to sell 500 kg tomatoes in Coimbatore'", font=font_body, fill=(148, 163, 184))

    draw.rounded_rectangle([(120, 670), (880, 830)], radius=8, fill=(15, 23, 42))
    draw.text((150, 695), "Why Voice is Essential for Rural Agriculture:", font=font_bold, fill=(245, 158, 11))
    draw.text((150, 735), "- Eliminates the barrier of mobile typing and English UI forms\n- Supports native Tamil dialects and traditional units (mootai, quintal)\n- Completes harvest listing in under 10 seconds in the field", font=font_body, fill=(203, 213, 225))

    draw.rounded_rectangle([(980, 110), (1840, 890)], radius=12, fill=(24, 32, 47), outline=(51, 65, 85), width=2)
    draw.text((1020, 140), "Muse Spark 1.3 Intent Extraction", font=font_h1, fill=(16, 185, 129))
    draw.text((1020, 195), "Validated Pydantic JSON Schema (/voice/intent)", font=font_body, fill=(148, 163, 184))

    draw.rounded_rectangle([(1020, 240), (1800, 650)], radius=12, fill=(10, 14, 23), outline=(16, 185, 129), width=2)
    json_lines = [
        "// HTTP 200 OK — Structured Pydantic Output",
        "{",
        '  "status": "success",',
        '  "model": "muse-spark-1.3",',
        '  "intent": {',
        '    "crop_type": "tomato",',
        '    "quantity_kg": 500.0,',
        '    "district": "Coimbatore",',
        '    "missing": [],',
        '    "action": "CREATE_LISTING"',
        '  }',
        "}"
    ]
    y_json = 270
    for line in json_lines:
        col = (148, 163, 184) if line.startswith("//") else (52, 211, 153)
        draw.text((1060, y_json), line, font=font_code, fill=col)
        y_json += 30

    draw.rounded_rectangle([(1020, 690), (1800, 830)], radius=8, fill=(15, 23, 42), outline=(59, 130, 246), width=2)
    draw.text((1050, 715), "STRICT EXTRACTION CONSTRAINTS:", font=font_bold, fill=(59, 130, 246))
    draw.text((1050, 750), "- 1 quintal = 100 kg, 1 tonne = 1000 kg\n- Bags without weight left null and placed in 'missing'\n- 'Never Guess' prompt rule guarantees zero hallucinations", font=font_body, fill=(203, 213, 225))

def render_scene_5(draw, progress):
    draw.rounded_rectangle([(80, 110), (920, 890)], radius=12, fill=(24, 32, 47), outline=(51, 65, 85), width=2)
    draw.text((120, 140), "Autonomous Post-Harvest Advisor", font=font_h1, fill=(245, 158, 11))
    draw.text((120, 195), "Dynamic Allocation Split based on Real-Time Market Demand", font=font_body, fill=(148, 163, 184))

    allocs = [
        ("Sell Today (Local Mandi)", "200 kg @ Rs 25/kg = Rs 5,000", "Captures immediate high local demand", (16, 185, 129)),
        ("Cold Storage Allocation", "300 kg @ Rs 35/kg (Expected)", "Holds produce for forecasted 10-day price rally", (59, 130, 246)),
        ("Food Processing Facility", "0 kg (Not needed for Grade A)", "Used only when shelf-life risk is elevated", (148, 163, 184))
    ]
    y = 250
    for ch_title, ch_val, ch_note, col in allocs:
        draw.rounded_rectangle([(120, y), (880, y + 100)], radius=8, fill=(15, 23, 42), outline=col, width=2)
        draw.text((140, y + 12), ch_title, font=font_bold, fill=col)
        draw.text((140, y + 42), ch_val, font=font_h2, fill=(248, 250, 252))
        draw.text((140, y + 74), ch_note, font=font_body, fill=(148, 163, 184))
        y += 120

    draw.rounded_rectangle([(120, 640), (880, 830)], radius=8, fill=(30, 41, 59), outline=(16, 185, 129), width=2)
    draw.text((140, 660), "Geographic Logistics Pooling (DBSCAN 8km)", font=font_bold, fill=(16, 185, 129))
    draw.text((140, 700), "Combines nearby farmers' produce into single shared truckloads.\nReduces freight expense by 45%, unlocking distant metropolitan markets.", font=font_body, fill=(203, 213, 225))
    draw.text((140, 780), "Result: Coimbatore Pool #104 Active (3 Farmers, 1.8 Tonnes)", font=font_bold, fill=(6, 182, 212))

    draw.rounded_rectangle([(980, 110), (1840, 890)], radius=12, fill=(24, 32, 47), outline=(51, 65, 85), width=2)
    draw.text((1020, 140), "Strict Numeric Integrity Guardrail", font=font_h1, fill=(16, 185, 129))
    draw.text((1020, 195), "Mathematical Ground Truth vs. LLM Natural Language", font=font_body, fill=(148, 163, 184))

    draw.rounded_rectangle([(1020, 240), (1800, 520)], radius=12, fill=(15, 23, 42), outline=(16, 185, 129), width=2)
    draw.text((1050, 260), "HOW THE GUARDRAIL PROTECTS FARMERS:", font=font_bold, fill=(16, 185, 129))

    flow_lines = [
        "1. Backend calculates exact rupee values & quantities deterministically.",
        "2. Muse Spark 1.3 translates facts into natural Tamil prose.",
        "3. Regex Guardrail scans output text: _numbers(generated_text).",
        "4. If text contains ANY number not in verified facts -> DISCARD.",
        "5. Farmer NEVER receives hallucinated prices or imaginary figures."
    ]
    y_flow = 310
    for l in flow_lines:
        draw.text((1050, y_flow), l, font=font_body, fill=(226, 232, 240))
        y_flow += 38

    draw.rounded_rectangle([(1020, 560), (1800, 830)], radius=8, fill=(10, 14, 23), outline=(59, 130, 246), width=2)
    draw.text((1050, 585), "// advisor_explainer.py — Regex Guardrail Logic", font=font_code, fill=(148, 163, 184))
    
    code_lines = [
        "def explain(facts: dict, lang: str = 'ta') -> Optional[str]:",
        "    allowed_numbers = _numbers_in_facts(facts)",
        "    text = ask_text(system=PROMPT, user=json.dumps(facts))",
        "    if not _numbers(text).issubset(allowed_numbers):",
        "        log.error('Halting: LLM invented figures not in facts!')",
        "        return None  # Fail safe! Zero hallucination reached"
    ]
    y_c = 625
    for cl in code_lines:
        col = (239, 68, 68) if 'None' in cl else (52, 211, 153)
        draw.text((1050, y_c), cl, font=font_code, fill=col)
        y_c += 32

def render_scene_6(draw, progress):
    draw.rounded_rectangle([(80, 110), (920, 890)], radius=12, fill=(24, 32, 47), outline=(51, 65, 85), width=2)
    draw.text((120, 140), "Enterprise Production Stack", font=font_h1, fill=(6, 182, 212))
    components = [
        ("FastAPI 0.115 Engine", "High-performance async web framework with Swagger OpenAPI documentation."),
        ("PostgreSQL + PostGIS", "Spatial database powering radius queries for logistics pooling."),
        ("Celery Task Queue", "Asynchronous processing of heavy Meta AI vision audits & PDF invoices."),
        ("Redis Budget Gatekeeper", "Enforces strict daily budget caps (2,000 calls/day hard limit).")
    ]
    y = 220
    for title, desc in components:
        draw.rounded_rectangle([(120, y), (880, y + 80)], radius=8, fill=(15, 23, 42), outline=(51, 65, 85), width=2)
        draw.text((140, y + 12), title, font=font_bold, fill=(6, 182, 212))
        draw.text((140, y + 42), desc, font=font_body, fill=(203, 213, 225))
        y += 105

    draw.rounded_rectangle([(120, 680), (880, 830)], radius=8, fill=(30, 41, 59))
    draw.text((140, 705), "Security & Rate Limiting:", font=font_bold, fill=(245, 158, 11))
    draw.text((140, 745), "Redis atomically increments call counters across all workers.\nA runaway worker or loop is physically incapable of burning API credits.", font=font_body, fill=(148, 163, 184))

    draw.rounded_rectangle([(980, 110), (1840, 890)], radius=12, fill=(24, 32, 47), outline=(51, 65, 85), width=2)
    draw.text((1020, 140), "Test Verification & Deployment", font=font_h1, fill=(16, 185, 129))

    draw.rounded_rectangle([(1020, 220), (1800, 360)], radius=12, fill=(15, 23, 42), outline=(16, 185, 129), width=2)
    draw.text((1060, 250), "29 / 29 PYTEST TESTS PASSING (100%)", font=font_h1, fill=(16, 185, 129))
    draw.text((1060, 305), "Full coverage across Auth, Logistics, Pricing, Meta AI, and Post-Harvest.", font=font_body, fill=(203, 213, 225))

    draw.rounded_rectangle([(1020, 400), (1800, 620)], radius=8, fill=(15, 23, 42), outline=(59, 130, 246), width=2)
    draw.text((1050, 425), "OPEN SOURCE & PRODUCTION REPOSITORY:", font=font_bold, fill=(59, 130, 246))
    draw.text((1050, 465), "GitHub: github.com/NivairaaWhite/uzhavan-ai-meta", font=font_code, fill=(248, 250, 252))
    draw.text((1050, 505), "- Branch 'main': Verified production integration", font=font_body, fill=(203, 213, 225))
    draw.text((1050, 540), "- Branch 'meta-ai': Multi-model implementation (Spark, Wonder, SAM)", font=font_body, fill=(203, 213, 225))
    draw.text((1050, 575), "- Tag 'baseline': Untouched starting snapshot", font=font_body, fill=(203, 213, 225))

    draw.rounded_rectangle([(1020, 660), (1800, 840)], radius=12, fill=(16, 185, 129))
    draw.text((1080, 700), "UZHAVAN.AI", font=font_brand, fill=(15, 23, 42))
    draw.text((1080, 750), "Bridging Edge Computing and Advanced Cloud AI for Indian Agriculture.", font=font_h2, fill=(15, 23, 42))
    draw.text((1080, 790), "Thank you.", font=font_bold, fill=(15, 23, 42))

def main():
    print(f"Generating 3-Minute Video ({TOTAL_SECONDS}s, {TOTAL_FRAMES} frames @ {FPS} fps)...")
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "rgba",
        "-r", str(FPS),
        "-i", "-",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "medium",
        "-crf", "20",
        OUTPUT_PATH
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    scene_renderers = [render_scene_1, render_scene_2, render_scene_3, render_scene_4, render_scene_5, render_scene_6]

    for frame_idx in range(TOTAL_FRAMES):
        current_sec = frame_idx / FPS
        scene_idx = min(int(current_sec // SCENE_DURATION), 5)
        scene_progress = (frame_idx % FRAMES_PER_SCENE) / FRAMES_PER_SCENE

        img = Image.new("RGBA", (WIDTH, HEIGHT), (11, 15, 25, 255))
        draw = ImageDraw.Draw(img)

        scene_renderers[scene_idx](draw, scene_progress)
        draw_header_and_footer(draw, frame_idx)

        proc.stdin.write(img.tobytes())

        if frame_idx % 100 == 0:
            print(f"Progress: frame {frame_idx}/{TOTAL_FRAMES} ({frame_idx/TOTAL_FRAMES*100:.1f}%) - {current_sec:.1f}s", flush=True)

    proc.stdin.close()
    stderr = proc.stderr.read().decode()
    proc.wait()

    if proc.returncode != 0:
        print("FFmpeg error:", stderr)
        sys.exit(1)

    print(f"\nSUCCESS! 3-Minute MP4 Video generated at:\n{OUTPUT_PATH}")

if __name__ == "__main__":
    main()
