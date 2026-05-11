import gradio as gr
import database
import json
import uuid
from dotenv import load_dotenv
from logo import LOGO_B64

load_dotenv()
database.init_db()

# ── AI Service ───────────────────────────────────────────────
from ai_service import ai_generate, extract_json

def ai_call(prompt, image=None, response_mime_type=None):
    return ai_generate(prompt, image=image, response_mime_type=response_mime_type)

def get_profile(uid):
    p = database.get_user_profile(uid) or {}
    parts = []
    for k, l in [("full_name","Name"),("age","Age"),("gender","Gender"),
                  ("weight","Weight"),("height","Height"),("activity_level","Activity"),
                  ("dietary_preference","Diet"),("fitness_goal","Goal"),
                  ("medical_conditions","Medical"),("allergies","Allergies")]:
        v = p.get(k)
        if v: parts.append(f"{l}: {v}")
    return "\n".join(parts), p.get("full_name","")

def analyze_label(image, uid):
    profile_text, _ = get_profile(uid)
    prompt = f"""You are Nova, a clinical nutrition AI.
USER MEDICAL PROFILE:
{profile_text}

Analyze the nutrition label image.
CRITICAL: You must evaluate if the product is safe given the user's specific medical conditions and allergies listed above.
Return ONLY valid JSON:
{{"product_name":"...","safety_label":"SAFE|CAUTION|AVOID","score":0-100,
  "serving_size":"...","calories":"...",
  "macros":[{{"nutrient":"Total Fat","amount":"..."}},{{"nutrient":"Saturated Fat","amount":"..."}},{{"nutrient":"Trans Fat","amount":"..."}},{{"nutrient":"Cholesterol","amount":"..."}},{{"nutrient":"Sodium","amount":"..."}},{{"nutrient":"Carbohydrates","amount":"..."}},{{"nutrient":"Dietary Fiber","amount":"..."}},{{"nutrient":"Total Sugars","amount":"..."}},{{"nutrient":"Added Sugars","amount":"..."}},{{"nutrient":"Protein","amount":"..."}}],
  "micros":[{{"nutrient":"Vitamin D","amount":"..."}},{{"nutrient":"Calcium","amount":"..."}},{{"nutrient":"Iron","amount":"..."}},{{"nutrient":"Potassium","amount":"..."}}],
  "ingredients":[{{"name":"...","status":"BENEFICIAL|HARMFUL|NEUTRAL|ALLERGY_CHECK","reason":"..."}}],
  "recommendation":"..."}}"""
    raw = ai_call(prompt, image=image, response_mime_type="application/json")
    if raw == "__OFFLINE__":
        return {
            "product_name": "Service Busy",
            "safety_label": "CAUTION",
            "score": 50,
            "serving_size": "N/A", "calories": "N/A",
            "macros": [{"nutrient": n, "amount": "N/A"} for n in ["Total Fat", "Saturated Fat", "Trans Fat", "Cholesterol", "Sodium", "Carbohydrates", "Dietary Fiber", "Total Sugars", "Added Sugars", "Protein"]],
            "micros": [{"nutrient": n, "amount": "N/A"} for n in ["Vitamin D", "Calcium", "Iron", "Potassium"]],
            "ingredients": [],
            "recommendation": "The AI service is currently at capacity or rate-limited. Please wait a few moments and try again."
        }
        
    data = extract_json(raw)
    if data:
        return data
    
    return {
        "product_name": "API Parse Error",
        "safety_label": "CAUTION",
        "score": 50,
        "serving_size": "N/A", "calories": "N/A",
        "macros": [{"nutrient": n, "amount": "N/A"} for n in ["Total Fat", "Saturated Fat", "Trans Fat", "Cholesterol", "Sodium", "Carbohydrates", "Dietary Fiber", "Total Sugars", "Added Sugars", "Protein"]],
        "micros": [{"nutrient": n, "amount": "N/A"} for n in ["Vitamin D", "Calcium", "Iron", "Potassium"]],
        "ingredients": [],
        "recommendation": f"RAW OUTPUT: {raw}"
    }

def build_result_html(d):
    sl = d.get("safety_label","CAUTION")
    # Vibrant Status styling
    col = {"SAFE":"#10b981","AVOID":"#ef4444"}.get(sl,"#f59e0b")
    bg_col = {"SAFE":"#d1fae5","AVOID":"#fee2e2"}.get(sl,"#fef3c7")
    score = d.get("score",0)
    macro_rows = "".join(
        f"<tr><td style='padding:14px 18px;border-bottom:1px solid #e5e7eb;color:#374151;font-weight:500;'>{r['nutrient']}</td>"
        f"<td style='padding:14px 18px;border-bottom:1px solid #e5e7eb;color:#111827;text-align:right;font-weight:800;'>{r['amount']}</td></tr>"
        for r in d.get("macros",[]))
    micro_rows = "".join(
        f"<tr><td style='padding:14px 18px;border-bottom:1px solid #e5e7eb;color:#374151;font-weight:500;'>{r['nutrient']}</td>"
        f"<td style='padding:14px 18px;border-bottom:1px solid #e5e7eb;color:#111827;text-align:right;font-weight:800;'>{r['amount']}</td></tr>"
        for r in d.get("micros",[]))
    ings = ""
    for ing in d.get("ingredients",[]):
        st = ing.get("status","NEUTRAL")
        icon = {"BENEFICIAL":"✨","HARMFUL":"⚠️","ALLERGY_CHECK":"🚨"}.get(st,"ℹ️")
        c2   = {"BENEFICIAL":"#10b981","HARMFUL":"#ef4444","ALLERGY_CHECK":"#f97316"}.get(st,"#6b7280")
        ings += (f"<li style='margin-bottom:16px;display:flex;gap:16px;background:#ffffff;padding:16px;border-radius:16px;border:1px solid #e5e7eb;box-shadow:0 4px 6px -1px rgba(0,0,0,0.05);'>"
                 f"<span style='font-size:1.4rem;font-weight:900;color:{c2};'>{icon}</span><div>"
                 f"<strong style='color:#111827;font-size:1.1rem;font-weight:900;'>{ing['name']}</strong> "
                 f"<span style='color:{c2};font-size:0.75rem;text-transform:uppercase;font-weight:800;letter-spacing:1px;margin-left:8px;padding:2px 8px;border-radius:12px;background:{c2}20;'>{st.replace('_',' ')}</span>"
                 f"<p style='margin:6px 0 0;color:#4b5563;font-size:0.95rem;line-height:1.5;font-weight:500;'>{ing['reason']}</p>"
                 f"</div></li>")
    tbl = (f"<table style='width:100%;border-collapse:collapse;background:#ffffff;"
           f"border:1px solid #e5e7eb;border-radius:16px;overflow:hidden;margin-bottom:12px;box-shadow:0 4px 6px rgba(0,0,0,0.02);'>"
           f"<thead><tr style='background:#f8fafc;'>"
           f"<th style='padding:14px 18px;text-align:left;color:#475569;font-size:0.85rem;font-weight:800;text-transform:uppercase;letter-spacing:1px;'>Nutrient</th>"
           f"<th style='padding:14px 18px;text-align:right;color:#475569;font-size:0.85rem;font-weight:800;text-transform:uppercase;letter-spacing:1px;'>Amount</th>"
           f"</tr></thead><tbody>{{rows}}</tbody></table>")
    
    return f"""<div style='font-family:Inter,sans-serif;padding:32px;background:rgba(255,255,255,0.9);backdrop-filter:blur(10px);border-radius:24px;border:1px solid #e5e7eb;box-shadow:0 10px 25px rgba(0,0,0,0.05);margin-bottom:20px;'>
<div style='text-align:center;margin-bottom:32px;'>
  <p style='color:#64748b;font-size:0.85rem;font-weight:800;letter-spacing:2px;text-transform:uppercase;margin:0 0 12px;'>Analysis Complete</p>
  <h1 style='font-size:2.4rem;font-weight:900;color:#0f172a;margin:0 0 16px;line-height:1.1;letter-spacing:-1px;'>{d.get('product_name','Product')}</h1>
  <div style='display:inline-flex;align-items:center;gap:12px;background:{bg_col};padding:10px 24px;border-radius:100px;border:1px solid {col}40;'>
    <span style='color:{col};font-weight:900;font-size:1.1rem;letter-spacing:1px;'>{sl}</span>
    <span style='color:{col}80;'>|</span>
    <span style='color:{col};font-weight:700;font-size:1.1rem;'>Score: {score}</span>
  </div>
</div>

<div style='display:flex;gap:16px;margin-bottom:32px;background:#ffffff;padding:20px;border-radius:16px;border:1px solid #e5e7eb;box-shadow:0 4px 6px rgba(0,0,0,0.02);'>
  <div style='flex:1;text-align:center;'><p style='margin:0;color:#64748b;font-size:0.85rem;font-weight:800;text-transform:uppercase;letter-spacing:1px;'>Serving</p><p style='margin:8px 0 0;color:#0f172a;font-weight:900;font-size:1.2rem;'>{d.get('serving_size','N/A')}</p></div>
  <div style='width:1px;background:#e2e8f0;'></div>
  <div style='flex:1;text-align:center;'><p style='margin:0;color:#64748b;font-size:0.85rem;font-weight:800;text-transform:uppercase;letter-spacing:1px;'>Calories</p><p style='margin:8px 0 0;color:#0f172a;font-weight:900;font-size:1.2rem;'>{d.get('calories','N/A')}</p></div>
</div>

<details class='glass-accordion' style='margin-bottom:32px;border:1px solid #e5e7eb;border-radius:16px;overflow:hidden;box-shadow:0 4px 6px rgba(0,0,0,0.02);background:#ffffff;'>
  <summary style='padding:20px;background:#f8fafc;font-weight:900;color:#0f172a;cursor:pointer;list-style:none;display:flex;justify-content:space-between;align-items:center;font-size:1.1rem;text-transform:uppercase;letter-spacing:1px;'>
    View Detailed Macros
  </summary>
  <div style='padding:24px;border-top:1px solid #e5e7eb;'>
    <h2 style='font-size:1.1rem;font-weight:900;color:#0f172a;margin:0 0 16px;text-transform:uppercase;letter-spacing:1px;'>Macronutrients</h2>
    {tbl.format(rows=macro_rows)}
    <h2 style='font-size:1.1rem;font-weight:900;color:#0f172a;margin:32px 0 16px;text-transform:uppercase;letter-spacing:1px;'>Micronutrients</h2>
    {tbl.format(rows=micro_rows)}
  </div>
</details>

<h2 style='font-size:1.4rem;font-weight:900;color:#0f172a;margin:0 0 20px;letter-spacing:-0.5px;'>
  Ingredient Assessment
</h2>
<ul style='list-style:none;margin:0 0 32px 0;padding:0;'>{ings or "<li style='color:#64748b;font-weight:600;'>No data available.</li>"}</ul>

<h2 style='font-size:1.4rem;font-weight:900;color:#0f172a;margin:0 0 16px;letter-spacing:-0.5px;'>
  Nova AI Verdict
</h2>
<p style='color:#334155;line-height:1.6;font-size:1.05rem;background:#f0fdf4;padding:24px;border-radius:16px;border:1px solid #10b981;margin:0;font-weight:500;'>{d.get('recommendation','')}</p>
</div>"""

def nova_chat(message, history, uid, scan_data):
    if not message.strip(): return history, ""
    pt, _ = get_profile(uid)
    pd = json.dumps(scan_data,indent=2) if scan_data else "No scan yet."
    
    hist_txt = ""
    if history:
        for m in history:
            role = "User" if m.get("role") == "user" else "Nova"
            hist_txt += f"{role}: {m.get('content')}\n"

    prompt = (f"You are Assistant Nova, an AI Dietary Concierge. Be concise, direct, and professional.\n"
              f"User Profile:\n{pt}\nProduct Scan Data:\n{pd}\n\n"
              f"Past Conversation:\n{hist_txt}\nUser's Message: {message}\n"
              f"Respond accurately taking their medical profile and constraints into account.")
              
    resp = ai_call(prompt)
    if resp == "__OFFLINE__": resp = "Nova is offline. Check API key or quotas."
    h = list(history or [])
    h.append({"role":"user","content":message})
    h.append({"role":"assistant","content":resp})
    return h, ""

# ── Vibrant Glassmorphism Theme ───────────────────────────────────
custom_theme = gr.themes.Soft(
    primary_hue=gr.themes.colors.emerald,
    neutral_hue=gr.themes.colors.slate,
    font=[gr.themes.GoogleFont("Inter"), "sans-serif"],
    radius_size=gr.themes.sizes.radius_lg,
).set(
    body_background_fill="#f0fdf4",
    block_background_fill="#ffffff",
    block_border_width="1px",
    block_border_color="#e5e7eb",
    block_shadow="0 10px 25px rgba(0,0,0,0.05)",
    button_primary_background_fill="#10b981",
    button_primary_background_fill_hover="#059669",
    button_primary_text_color="#ffffff",
    button_secondary_background_fill="#f1f5f9",
    button_secondary_background_fill_hover="#e2e8f0",
    button_secondary_text_color="#0f172a",
    input_background_fill="#f8fafc",
)

CSS = """
    /* Hide specific Gradio chrome */
    footer { display: none !important; }
    
    /* Vibrant Gradient Background */
    body, .gradio-container {
        background: linear-gradient(135deg, #f0fdf4 0%, #e0f2fe 100%) !important;
        background-attachment: fixed !important;
    }
    
    /* Global Nav Glassmorphism */
    .global-nav { 
        background: rgba(255, 255, 255, 0.8) !important; 
        backdrop-filter: blur(12px) !important;
        padding: 12px 20px; 
        border-radius: 16px; 
        border: 1px solid rgba(255,255,255,0.5) !important; 
        margin-bottom: 32px !important; 
        position: sticky; top: 12px; z-index: 1000; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.05) !important; 
    }
    
    /* Dynamic Buttons */
    .btn-3d {
        box-shadow: 0 4px 10px rgba(16, 185, 129, 0.3) !important;
        transform: translateY(0px) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        border: none !important;
        font-weight: 800 !important;
        letter-spacing: 0.5px !important;
    }
    .btn-3d:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 15px rgba(16, 185, 129, 0.4) !important;
    }
    .btn-3d:active {
        box-shadow: 0 2px 5px rgba(16, 185, 129, 0.3) !important;
        transform: translateY(1px) !important;
    }
    .btn-3d.secondary {
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05) !important;
        background: #ffffff !important;
        color: #10b981 !important;
        border: 1px solid #e5e7eb !important;
    }
    .btn-3d.secondary:hover {
        box-shadow: 0 6px 15px rgba(0, 0, 0, 0.08) !important;
        background: #f8fafc !important;
    }

    /* Page Fade & Slide Animation */
    @keyframes slideFadeUp {
        from { opacity: 0; transform: translateY(30px) scale(0.99); }
        to { opacity: 1; transform: translateY(0) scale(1); }
    }
    .page-fade-in {
        animation: slideFadeUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    /* Accordion */
    .glass-accordion summary::-webkit-details-marker { display: none; }
    .glass-accordion summary:after { content: '+'; float: right; font-weight: 900; color: #000; font-size: 1.4rem; }
    .glass-accordion[open] summary:after { content: '-'; }
"""

CAMERA_FIX_JS = """
<script>
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const oldGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
        navigator.mediaDevices.getUserMedia = function(constraints) {
            if (constraints && constraints.video) {
                if (typeof constraints.video === 'boolean') {
                    constraints.video = { facingMode: 'environment' };
                } else {
                    constraints.video.facingMode = 'environment';
                }
            }
            return oldGetUserMedia(constraints);
        };
    }
</script>
"""

# ── APP ──────────────────────────────────────────────────────
with gr.Blocks(title="PurePic – AI Nutrition", head=CAMERA_FIX_JS) as app:

    uid_st  = gr.State("")
    scan_st = gr.State(None)

    # ── Global Navigation Bar ──────────────────────────────
    with gr.Row(elem_classes="global-nav", visible=False) as nav_bar:
        nav_dash = gr.Button("Dashboard", variant="secondary", size="sm", elem_classes=["btn-3d", "secondary"])
        nav_scan = gr.Button("Scanner", variant="secondary", size="sm", elem_classes=["btn-3d", "secondary"])
        nav_nova = gr.Button("Nova AI", variant="secondary", size="sm", elem_classes=["btn-3d", "secondary"])
        nav_prof = gr.Button("Profile", variant="secondary", size="sm", elem_classes=["btn-3d", "secondary"])

    # ── SPLASH SCREEN ──────────────────────────────────────
    
    # ── SPA TABS CONTAINER ─────────────────────────────────
    with gr.Tabs(selected="splash", elem_classes="hide-tabs") as main_tabs:

        with gr.TabItem("Splash", id="splash") as page_splash:
            gr.HTML(f"""
            <div style='text-align:center;padding:80px 20px;max-width:500px;margin:40px auto;background:rgba(255,255,255,0.8);backdrop-filter:blur(16px);border-radius:32px;border:1px solid rgba(255,255,255,0.6);box-shadow:0 20px 40px rgba(0,0,0,0.08);'>
                <img src="{LOGO_B64}" style="width:160px; height:160px; object-fit:contain; margin:0 auto 32px auto; display:block; border-radius:32px; border:2px solid #e5e7eb; box-shadow:0 10px 25px rgba(0,0,0,0.05);"/>
                <h1 style='font-size:3.2rem;font-weight:900;background:linear-gradient(90deg, #10b981, #0ea5e9);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:0 0 12px;letter-spacing:-1px;'>PurePic</h1>
                <p style='font-size:1.1rem;color:#10b981;font-weight:800;margin:0 0 24px;text-transform:uppercase;letter-spacing:2px;'>Advanced Nutrition AI</p>
                <p style='color:#475569;margin:0 auto 40px;line-height:1.6;font-size:1.1rem;font-weight:500;'>Clinical-grade dietary analysis utilizing deep vision architecture.</p>
            </div>
            """)
            with gr.Row():
                with gr.Column(scale=1): pass
                with gr.Column(scale=2):
                    btn_go_login = gr.Button("Enter System", variant="primary", size="lg", elem_classes="btn-3d")
                with gr.Column(scale=1): pass

        # ── LOGIN SCREEN ───────────────────────────────────────
        with gr.TabItem("Login", id="login") as page_login:
            gr.HTML("""
            <div style='text-align:center;padding:20px;max-width:400px;margin:20px auto 0;'>
                <h1 style='font-size:2.4rem;font-weight:900;color:#0f172a;margin:0 0 8px;letter-spacing:-1px;'>Authentication</h1>
                <p style='color:#64748b;margin:0 0 20px;font-weight:600;letter-spacing:1px;text-transform:uppercase;font-size:0.85rem;'>Authorized Personnel Only</p>
            </div>
            """)
            with gr.Column(scale=1):
                with gr.Group():
                    in_user    = gr.Textbox(label="Username", placeholder="Enter username", show_label=False)
                    in_pass    = gr.Textbox(label="Password",  placeholder="Enter password", type="password", show_label=False)
                login_msg  = gr.HTML("")
                btn_signin = gr.Button("Authenticate", variant="primary", size="lg", elem_classes="btn-3d")
                btn_to_reg = gr.Button("Request Access", variant="secondary", elem_classes=["btn-3d", "secondary"])

        # ── REGISTER SCREEN ────────────────────────────────────
        with gr.TabItem("Register", id="register") as page_register:
            gr.HTML("""
            <div style='text-align:center;padding:20px;max-width:400px;margin:20px auto 0;'>
                <h1 style='font-size:2.4rem;font-weight:900;color:#0f172a;margin:0 0 8px;letter-spacing:-1px;'>Enrollment</h1>
                <p style='color:#64748b;margin:0 0 20px;font-weight:600;letter-spacing:1px;text-transform:uppercase;font-size:0.85rem;'>Create Identity Profile</p>
            </div>
            """)
            with gr.Column():
                with gr.Group():
                    reg_user   = gr.Textbox(label="Username",        placeholder="Choose username", show_label=False)
                    reg_pass   = gr.Textbox(label="Password",         placeholder="Choose password",   type="password", show_label=False)
                    reg_conf   = gr.Textbox(label="Confirm Password", placeholder="Verify password", type="password", show_label=False)
                reg_msg    = gr.HTML("")
                btn_reg    = gr.Button("Initialize Profile", variant="primary", size="lg", elem_classes="btn-3d")
                btn_to_log = gr.Button("Return to Auth", variant="secondary", elem_classes=["btn-3d", "secondary"])

        # ── ONBOARDING SCREEN ──────────────────────────────────
        with gr.TabItem("Onboarding", id="onboarding") as page_onboarding:
            gr.HTML("""
            <div style='padding:20px 0;'>
                <h1 style='font-size:2.6rem;font-weight:900;color:#0f172a;margin:0 0 8px;letter-spacing:-1px;'>Biological Data</h1>
                <p style='color:#64748b;margin:0 0 24px;font-size:1.05rem;font-weight:600;'>Establish parameters for AI clinical evaluation.</p>
            </div>
            """)
            with gr.Group():
                ob_name    = gr.Textbox(label="Full Name",   placeholder="Identity designation")
                with gr.Row():
                    ob_age     = gr.Number( label="Age",          value=25)
                    ob_gender  = gr.Radio(["Male","Female","Other"], label="Biological Sex", value="Male")
                with gr.Row():
                    ob_weight = gr.Textbox(label="Weight", placeholder="Mass (kg)")
                    ob_height = gr.Textbox(label="Height", placeholder="Height (cm)")
            
            with gr.Group():
                ob_activity = gr.Dropdown(["Sedentary","Lightly Active","Moderately Active","Very Active","Athlete"], label="Metabolic Output", value="Moderately Active")
                ob_diet = gr.Dropdown(["No Restriction","Vegetarian","Vegan","Keto","Diabetic-Friendly","Low Sodium"], label="Dietary Architecture", value="No Restriction")
                ob_goal = gr.Radio(["Weight Loss","Muscle Building","Maintenance","Disease Management","General Wellness"], label="Primary Objective", value="General Wellness")
            
            with gr.Group():
                ob_medical = gr.Textbox(label="Medical Conditions", placeholder="Specify pathologies (or 'None')")
                ob_allergy = gr.Textbox(label="Allergens", placeholder="Specify strict allergens (or 'None')")
        
            btn_ob = gr.Button("Commit Biological Data", variant="primary", size="lg", elem_classes="btn-3d")

        # ── DASHBOARD SCREEN ───────────────────────────────────
        with gr.TabItem("Dashboard", id="dashboard") as page_dashboard:
            dash_title = gr.HTML("")
        
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### SCAN MODULE\nDeploy optical analysis.")
                    btn_d_scan = gr.Button("Initialize Scanner", variant="primary", elem_classes="btn-3d")
                with gr.Column():
                    gr.Markdown("### NOVA TERMINAL\nAccess dietary AI.")
                    btn_d_nova = gr.Button("Connect Nova", variant="secondary", elem_classes=["btn-3d", "secondary"])

            gr.HTML("""
            <div style='display:grid;grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));gap:24px;margin-top:32px;'>
                <div style='background:rgba(255,255,255,0.8);backdrop-filter:blur(8px);border-radius:24px;padding:32px;border:1px solid rgba(255,255,255,0.6);box-shadow:0 8px 32px rgba(0,0,0,0.05);'>
                    <div style='font-size:2.4rem;margin-bottom:16px;color:#10b981;'>❖</div>
                    <h3 style='margin:0 0 8px;font-weight:900;color:#0f172a;letter-spacing:0.5px;font-size:1.2rem;'>Protocol Check</h3>
                    <p style='margin:0;color:#475569;font-size:0.95rem;font-weight:500;line-height:1.5;'>Automated alignment with biological parameters.</p>
                </div>
                <div style='background:rgba(255,255,255,0.8);backdrop-filter:blur(8px);border-radius:24px;padding:32px;border:1px solid rgba(255,255,255,0.6);box-shadow:0 8px 32px rgba(0,0,0,0.05);'>
                    <div style='font-size:2.4rem;margin-bottom:16px;color:#ef4444;'>⚠</div>
                    <h3 style='margin:0 0 8px;font-weight:900;color:#0f172a;letter-spacing:0.5px;font-size:1.2rem;'>Allergen Radar</h3>
                    <p style='margin:0;color:#475569;font-size:0.95rem;font-weight:500;line-height:1.5;'>Strict molecular hazard detection.</p>
                </div>
            </div>
            """)

        # ── SCANNER SCREEN ─────────────────────────────────────
        with gr.TabItem("Scanner", id="scanner") as page_scanner:
            gr.HTML("""
            <div style='padding:20px 0 10px;'>
                <h1 style='font-size:2.4rem;font-weight:900;color:#0f172a;margin:0 0 8px;letter-spacing:-1px;'>Optical Feed</h1>
                <p style='color:#64748b;margin:0;font-weight:600;letter-spacing:1px;font-size:0.85rem;'>Awaiting image payload.</p>
            </div>
            """)
            scan_img    = gr.Image(sources=["upload","webcam"], type="pil", label="FEED", elem_id="scan-img", height=400)
            scan_status = gr.HTML("")
            btn_analyze = gr.Button("Execute Analysis", variant="primary", size="lg", elem_classes="btn-3d")

        # ── RESULTS SCREEN ─────────────────────────────────────
        with gr.TabItem("Results", id="results") as page_results:
            result_html = gr.HTML("<p style='color:#666;padding:20px;text-align:center;font-weight:700;text-transform:uppercase;'>No data loaded.</p>")
            with gr.Row():
                btn_res_scan = gr.Button("New Scan", variant="secondary", elem_classes=["btn-3d", "secondary"])
                btn_res_nova = gr.Button("Forward to Nova", variant="primary", elem_classes="btn-3d")

        # ── NOVA AI SCREEN ─────────────────────────────────────
        with gr.TabItem("Nova", id="nova") as page_nova:
            gr.HTML("""
            <div style='text-align:center;padding:20px 0 24px;'>
                <div style='width:72px;height:72px;background:linear-gradient(135deg, #10b981, #0ea5e9);border-radius:24px;margin:0 auto 20px;display:flex;align-items:center;justify-content:center;box-shadow:0 8px 20px rgba(16,185,129,0.3);'>
                    <span style='font-size:2.2rem;color:white;'>✦</span>
                </div>
                <h1 style='font-size:2.2rem;font-weight:900;color:#0f172a;margin:0 0 8px;letter-spacing:-1px;'>Nova Terminal</h1>
                <p style='color:#10b981;font-weight:800;font-size:0.9rem;margin:0;text-transform:uppercase;letter-spacing:2px;'>System Online</p>
            </div>
            """)
            nova_chat_box = gr.Chatbot(height=500, show_label=False, avatar_images=(None, "https://ui-avatars.com/api/?name=Nova&background=000&color=fff"))
            with gr.Row():
                nova_msg = gr.Textbox(placeholder="Transmit query...", show_label=False, container=False, scale=4)
                btn_send = gr.Button("Transmit", variant="primary", scale=1, elem_classes="btn-3d")

        # ── PROFILE SCREEN ─────────────────────────────────────
        with gr.TabItem("Profile", id="profile") as page_profile:
            gr.HTML("""
            <div style='padding:20px 0 10px;'>
                <h1 style='font-size:2.4rem;font-weight:900;color:#0f172a;margin:0 0 8px;letter-spacing:-1px;'>Identity Matrix</h1>
                <p style='color:#64748b;margin:0;font-weight:600;letter-spacing:1px;font-size:0.85rem;'>Current parameters.</p>
            </div>
            """)
            with gr.Group():
                prof_md  = gr.Markdown(elem_classes="prose")
            with gr.Row():
                btn_edit = gr.Button("Modify Parameters", variant="primary", elem_classes="btn-3d")
                btn_lo   = gr.Button("Terminate Session", variant="secondary", elem_classes=["btn-3d", "secondary"])

        # ── ROUTING ENGINE ──────────────────────────────────────
    # Using Tab routing instead of manual visibility toggles for perfect SPA stability
    PAGES = ["splash", "login", "register", "onboarding", "dashboard", "scanner", "results", "nova", "profile"]
    
    def route(idx):
        return gr.update(selected=PAGES[idx])

    # Splash 
    btn_go_login.click(lambda: route(1), inputs=[], outputs=main_tabs)

    # Login / Register Toggle
    btn_to_reg.click(lambda: route(2), inputs=[], outputs=main_tabs)
    btn_to_log.click(lambda: route(1), inputs=[], outputs=main_tabs)

    # Sign In
    def do_signin(u, p):
        ERR = "<p style='color:#000;background:#f3f4f6;border-radius:12px;padding:16px;font-size:0.95rem;font-weight:800;margin-bottom:16px;border:2px solid #000;'>"
        if not u or not p:
            return ERR + "CREDENTIALS REQUIRED.</p>", "", "", route(1), gr.update(visible=False)
        user = database.get_user_by_username(u.strip().lower())
        if not user or user["password"] != p:
            return ERR + "AUTH FAILURE.</p>", "", "", route(1), gr.update(visible=False)
        uid  = user["id"]
        _, name = get_profile(uid)
        greet = (f"<div style='padding:24px 0;'><h1 style='font-size:2.8rem;font-weight:900;color:#000;margin:0 0 12px;line-height:1.1;letter-spacing:-1px;text-transform:uppercase;'>"
                 f"User: {name or u}</h1><p style='color:#666;font-size:1.1rem;margin:0;font-weight:700;letter-spacing:1px;text-transform:uppercase;'>Dashboard Authorized</p></div>")
        
        target = 4 if user["is_setup_complete"] else 3
        nav_vis = gr.update(visible=True) if user["is_setup_complete"] else gr.update(visible=False)
        return "", uid, greet, route(target), nav_vis

    btn_signin.click(
        do_signin,
        inputs=[in_user, in_pass],
        outputs=[login_msg, uid_st, dash_title, main_tabs, nav_bar]
    )

    # Register
    def do_reg(u, p, c):
        ERR = "<p style='color:#000;background:#f3f4f6;border-radius:12px;padding:16px;font-size:0.95rem;font-weight:800;margin-bottom:16px;border:2px solid #000;'>"
        if not u or not p:
            return ERR + "CREDENTIALS REQUIRED.</p>", "", route(2)
        if p != c:
            return ERR + "MISMATCH.</p>", "", route(2)
        uid = f"u{uuid.uuid4().hex[:8]}"
        if not database.create_user(uid, u.strip().lower(), p):
            return ERR + "IDENTITY EXISTS.</p>", "", route(2)
        return "", uid, route(3)

    btn_reg.click(
        do_reg,
        inputs=[reg_user, reg_pass, reg_conf],
        outputs=[reg_msg, uid_st, main_tabs]
    )

    # Onboarding
    def do_onboard(uid, name, age, gender, weight, height,
                   activity, diet, goal, medical, allergy):
        database.update_user_profile(uid, {
            "full_name": name, "age": str(int(age)) if age else "",
            "gender": gender or "", "weight": weight or "", "height": height or "",
            "activity_level": activity or "", "dietary_preference": diet or "",
            "fitness_goal": goal or "",
            "medical_complications": medical.strip() if medical else "None",
            "allergies": allergy.strip() if allergy else "None",
        })
        greet = (f"<div style='padding:24px 0;'><h1 style='font-size:2.8rem;font-weight:900;color:#000;margin:0 0 12px;line-height:1.1;letter-spacing:-1px;text-transform:uppercase;'>"
                 f"User: {name}</h1><p style='color:#666;font-size:1.1rem;margin:0;font-weight:700;letter-spacing:1px;text-transform:uppercase;'>Dashboard Authorized</p></div>")
        return greet, route(4), gr.update(visible=True)

    btn_ob.click(
        do_onboard,
        inputs=[uid_st, ob_name, ob_age, ob_gender, ob_weight, ob_height,
                ob_activity, ob_diet, ob_goal, ob_medical, ob_allergy],
        outputs=[dash_title, main_tabs, nav_bar]
    )

    # Global Navigation
    nav_dash.click(lambda: route(4), inputs=[], outputs=main_tabs)
    nav_scan.click(lambda: route(5), inputs=[], outputs=main_tabs)
    nav_nova.click(lambda: route(7), inputs=[], outputs=main_tabs)
    
    def open_prof(uid):
        _, _ = get_profile(uid)
        p = database.get_user_profile(uid) or {}
        md = "\n".join(
            f"**{k.replace('_',' ').upper()}**  \n> {v}  \n" for k, v in p.items() if v
        ) or "No data."
        return md, route(8)

    nav_prof.click(open_prof, inputs=[uid_st], outputs=[prof_md, main_tabs])

    # Dashboard Actions
    btn_d_scan.click(lambda: route(5), inputs=[], outputs=main_tabs)
    btn_d_nova.click(lambda: route(7), inputs=[], outputs=main_tabs)

    # Scanner
    LOAD_HTML = ("<div style='text-align:center;padding:80px 20px;background:#fff;border-radius:32px;box-shadow:0 12px 0 #000;border:4px solid #000;margin-top:32px;'>"
                 "<div style='font-size:4rem;margin-bottom:20px;animation: pulse 1s infinite;'>◷</div>"
                 "<h2 style='color:#000;font-weight:900;margin:0 0 12px;text-transform:uppercase;letter-spacing:1px;font-size:1.6rem;'>Processing</h2>"
                 "<p style='color:#666;margin:0;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;font-size:0.9rem;'>Extracting molecular data</p></div>")

    def do_analysis(img, uid, progress=gr.Progress()):
        progress(0, desc="System Init...")
        if img is None:
            return ("<div style='background:#f3f4f6;color:#000;padding:24px;border-radius:16px;border:2px solid #000;text-align:center;margin-top:32px;font-weight:900;text-transform:uppercase;letter-spacing:1px;'>PAYLOAD REQUIRED.</div>",
                    None, route(5))
        progress(0.4, desc="Parsing Image Data...")
        d = analyze_label(img, uid)
        progress(1.0, desc="Complete")
        return build_result_html(d), d, route(6)

    btn_analyze.click(
        lambda: (LOAD_HTML, None),
        inputs=None, outputs=[scan_status, scan_st]
    ).then(
        do_analysis,
        inputs=[scan_img, uid_st],
        outputs=[result_html, scan_st, main_tabs]
    )

    # Results
    btn_res_scan.click(lambda: route(5), inputs=[], outputs=main_tabs)
    btn_res_nova.click(lambda: route(7), inputs=[], outputs=main_tabs)

    # Nova Chat
    btn_send.click(
        nova_chat, inputs=[nova_msg, nova_chat_box, uid_st, scan_st],
        outputs=[nova_chat_box, nova_msg]
    )
    nova_msg.submit(
        nova_chat, inputs=[nova_msg, nova_chat_box, uid_st, scan_st],
        outputs=[nova_chat_box, nova_msg]
    )

    # Profile
    btn_edit.click(lambda: route(3), inputs=[], outputs=main_tabs)
    btn_lo.click(lambda: ("", None, route(0), gr.update(visible=False)), inputs=[], outputs=[uid_st, scan_st, main_tabs, nav_bar])

if __name__ == "__main__":
    database.init_db()
    app.launch(server_name="0.0.0.0", server_port=7860, show_error=True, theme=custom_theme, css=CSS)
