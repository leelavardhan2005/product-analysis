import streamlit as st
import database
import json
import uuid
import os
from PIL import Image
from logo import LOGO_B64
from ai_service import ai_generate, extract_json

# Initialize database
database.init_db()

# Page configuration
st.set_page_config(
    page_title="PurePic – AI Nutrition",
    page_icon="🥦",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for styling
st.markdown("""
<style>
    /* Styling for glassmorphism panels */
    .glass-panel {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(12px);
        border-radius: 24px;
        padding: 32px;
        border: 1px solid rgba(255, 255, 255, 0.5);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
        margin-bottom: 24px;
    }
    
    /* Navigation styling */
    .nav-container {
        display: flex;
        justify-content: space-around;
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 12px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 32px;
    }
    
    /* Buttons */
    .stButton>button {
        border-radius: 12px;
        font-weight: 700;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if "page" not in st.session_state:
    st.session_state.page = "splash"
if "uid" not in st.session_state:
    st.session_state.uid = ""
if "username" not in st.session_state:
    st.session_state.username = ""
if "scan_st" not in st.session_state:
    st.session_state.scan_st = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def navigate_to(page):
    st.session_state.page = page
    st.rerun()

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
  
    raw = ai_generate(prompt, image=image, response_mime_type="application/json")
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
    if not message.strip(): return history
    pt, _ = get_profile(uid)
    pd = json.dumps(scan_data, indent=2) if scan_data else "No scan yet."
    
    hist_txt = ""
    for m in history:
        role = "User" if m["role"] == "user" else "Nova"
        hist_txt += f"{role}: {m['content']}\n"

    prompt = (f"You are Assistant Nova, an AI Dietary Concierge. Be concise, direct, and professional.\n"
              f"User Profile:\n{pt}\nProduct Scan Data:\n{pd}\n\n"
              f"Past Conversation:\n{hist_txt}\nUser's Message: {message}\n"
              f"Respond accurately taking their medical profile and constraints into account.")
              
    resp = ai_generate(prompt)
    if resp == "__OFFLINE__": resp = "Nova is offline. Check API key or quotas."
    
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": resp})
    return history


# Navigation Header Component
def render_nav():
    if st.session_state.uid:
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            if st.button("Dashboard", use_container_width=True):
                navigate_to("dashboard")
        with col2:
            if st.button("Scanner", use_container_width=True):
                navigate_to("scanner")
        with col3:
            if st.button("Nova AI", use_container_width=True):
                navigate_to("nova")
        with col4:
            if st.button("Profile", use_container_width=True):
                navigate_to("profile")
        with col5:
            if st.button("Logout", use_container_width=True):
                st.session_state.uid = ""
                st.session_state.username = ""
                st.session_state.scan_st = None
                st.session_state.chat_history = []
                navigate_to("splash")
        st.markdown("<hr style='margin: 12px 0 24px 0;'/>", unsafe_allow_html=True)


# Render Pages based on state
if st.session_state.page == "splash":
    st.markdown(f"""
    <div style='text-align:center;padding:40px 20px;margin-top:20px;'>
        <img src="{LOGO_B64}" style="width:160px; height:160px; object-fit:contain; margin:0 auto 32px auto; display:block; border-radius:32px; border:2px solid #e5e7eb; box-shadow:0 10px 25px rgba(0,0,0,0.05);"/>
        <h1 style='font-size:3.2rem;font-weight:900;background:linear-gradient(90deg, #10b981, #0ea5e9);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:0 0 12px;letter-spacing:-1px;'>PurePic</h1>
        <p style='font-size:1.1rem;color:#10b981;font-weight:800;margin:0 0 24px;text-transform:uppercase;letter-spacing:2px;'>Advanced Nutrition AI</p>
        <p style='color:#475569;margin:0 auto 40px;line-height:1.6;font-size:1.1rem;font-weight:500;'>Clinical-grade dietary analysis utilizing deep vision architecture.</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Enter System", type="primary", use_container_width=True):
        navigate_to("login")

elif st.session_state.page == "login":
    st.markdown("""
    <div style='text-align:center;margin-top:20px;'>
        <h1 style='font-size:2.4rem;font-weight:900;color:#0f172a;margin:0 0 8px;letter-spacing:-1px;'>Authentication</h1>
        <p style='color:#64748b;margin:0 0 20px;font-weight:600;letter-spacing:1px;text-transform:uppercase;font-size:0.85rem;'>Authorized Personnel Only</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        u = st.text_input("Username", placeholder="Enter username")
        p = st.text_input("Password", type="password", placeholder="Enter password")
        submitted = st.form_submit_button("Authenticate", use_container_width=True)
        
        if submitted:
            if not u or not p:
                st.error("Credentials required.")
            else:
                user = database.get_user_by_username(u.strip().lower())
                if not user or user["password"] != p:
                    st.error("Auth failure.")
                else:
                    st.session_state.uid = user["id"]
                    st.session_state.username = u.strip().lower()
                    if user["is_setup_complete"]:
                        navigate_to("dashboard")
                    else:
                        navigate_to("onboarding")
                        
    if st.button("Request Access", use_container_width=True):
        navigate_to("register")

elif st.session_state.page == "register":
    st.markdown("""
    <div style='text-align:center;margin-top:20px;'>
        <h1 style='font-size:2.4rem;font-weight:900;color:#0f172a;margin:0 0 8px;letter-spacing:-1px;'>Enrollment</h1>
        <p style='color:#64748b;margin:0 0 20px;font-weight:600;letter-spacing:1px;text-transform:uppercase;font-size:0.85rem;'>Create Identity Profile</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("register_form"):
        u = st.text_input("Username", placeholder="Choose username")
        p = st.text_input("Password", type="password", placeholder="Choose password")
        c = st.text_input("Confirm Password", type="password", placeholder="Verify password")
        submitted = st.form_submit_button("Initialize Profile", use_container_width=True)
        
        if submitted:
            if not u or not p:
                st.error("Credentials required.")
            elif p != c:
                st.error("Passwords mismatch.")
            else:
                uid = f"u{uuid.uuid4().hex[:8]}"
                if not database.create_user(uid, u.strip().lower(), p):
                    st.error("Identity exists.")
                else:
                    st.session_state.uid = uid
                    st.session_state.username = u.strip().lower()
                    st.success("Account created successfully!")
                    navigate_to("onboarding")
                    
    if st.button("Return to Auth", use_container_width=True):
        navigate_to("login")

elif st.session_state.page == "onboarding":
    st.markdown("""
    <div style='padding:10px 0;'>
        <h1 style='font-size:2.6rem;font-weight:900;color:#0f172a;margin:0 0 8px;letter-spacing:-1px;'>Biological Data</h1>
        <p style='color:#64748b;margin:0 0 24px;font-size:1.05rem;font-weight:600;'>Establish parameters for AI clinical evaluation.</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("onboarding_form"):
        name = st.text_input("Full Name", placeholder="Identity designation")
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Age", min_value=1, max_value=120, value=25)
        with col2:
            gender = st.radio("Biological Sex", ["Male", "Female", "Other"], index=0)
            
        col3, col4 = st.columns(2)
        with col3:
            weight = st.text_input("Weight", placeholder="Mass (kg)")
        with col4:
            height = st.text_input("Height", placeholder="Height (cm)")
            
        activity = st.selectbox("Metabolic Output", ["Sedentary", "Lightly Active", "Moderately Active", "Very Active", "Athlete"], index=2)
        diet = st.selectbox("Dietary Architecture", ["No Restriction", "Vegetarian", "Vegan", "Keto", "Diabetic-Friendly", "Low Sodium"], index=0)
        goal = st.radio("Primary Objective", ["Weight Loss", "Muscle Building", "Maintenance", "Disease Management", "General Wellness"], index=4)
        
        medical = st.text_input("Medical Conditions", placeholder="Specify pathologies (or 'None')")
        allergy = st.text_input("Allergens", placeholder="Specify strict allergens (or 'None')")
        
        submitted = st.form_submit_button("Commit Biological Data", use_container_width=True)
        if submitted:
            database.update_user_profile(st.session_state.uid, {
                "full_name": name,
                "age": str(int(age)) if age else "",
                "gender": gender or "",
                "weight": weight or "",
                "height": height or "",
                "activity_level": activity or "",
                "dietary_preference": diet or "",
                "fitness_goal": goal or "",
                "medical_conditions": medical.strip() if medical else "None",
                "allergies": allergy.strip() if allergy else "None",
            })
            st.success("Biological data committed!")
            navigate_to("dashboard")

elif st.session_state.page == "dashboard":
    render_nav()
    _, name = get_profile(st.session_state.uid)
    
    st.markdown(f"""
    <div style='padding:10px 0;'>
        <h1 style='font-size:2.8rem;font-weight:900;color:#0f172a;margin:0 0 12px;line-height:1.1;letter-spacing:-1px;text-transform:uppercase;'>User: {name or st.session_state.username}</h1>
        <p style='color:#64748b;font-size:1.1rem;margin:0;font-weight:700;letter-spacing:1px;text-transform:uppercase;'>Dashboard Authorized</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### SCAN MODULE\nDeploy optical analysis.")
        if st.button("Initialize Scanner", type="primary", use_container_width=True):
            navigate_to("scanner")
    with col2:
        st.markdown("### NOVA TERMINAL\nAccess dietary AI.")
        if st.button("Connect Nova", use_container_width=True):
            navigate_to("nova")
            
    st.markdown("""
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
    """, unsafe_allow_html=True)

elif st.session_state.page == "scanner":
    render_nav()
    st.markdown("""
    <div style='padding:10px 0;'>
        <h1 style='font-size:2.4rem;font-weight:900;color:#0f172a;margin:0 0 8px;letter-spacing:-1px;'>Optical Feed</h1>
        <p style='color:#64748b;margin:0;font-weight:600;letter-spacing:1px;font-size:0.85rem;'>Awaiting image payload.</p>
    </div>
    """, unsafe_allow_html=True)
    
    img_file = st.file_uploader("Upload Nutrition Label Image", type=["png", "jpg", "jpeg"])
    camera_file = st.camera_input("Take a photo of Nutrition Label")
    
    active_file = img_file or camera_file
    
    if active_file:
        img = Image.open(active_file)
        st.image(img, caption="Loaded Payload", use_container_width=True)
        
        if st.button("Execute Analysis", type="primary", use_container_width=True):
            with st.spinner("Extracting molecular data..."):
                res = analyze_label(img, st.session_state.uid)
                st.session_state.scan_st = res
                navigate_to("results")

elif st.session_state.page == "results":
    render_nav()
    if st.session_state.scan_st is None:
        st.warning("No scan data found. Please run the scanner first.")
        if st.button("Go to Scanner", use_container_width=True):
            navigate_to("scanner")
    else:
        html_content = build_result_html(st.session_state.scan_st)
        st.components.v1.html(html_content, height=800, scrolling=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("New Scan", use_container_width=True):
                st.session_state.scan_st = None
                navigate_to("scanner")
        with col2:
            if st.button("Forward to Nova", type="primary", use_container_width=True):
                navigate_to("nova")

elif st.session_state.page == "nova":
    render_nav()
    st.markdown("""
    <div style='text-align:center;padding:10px 0;'>
        <div style='width:72px;height:72px;background:linear-gradient(135deg, #10b981, #0ea5e9);border-radius:24px;margin:0 auto 20px;display:flex;align-items:center;justify-content:center;box-shadow:0 8px 20px rgba(16,185,129,0.3);'>
            <span style='font-size:2.2rem;color:white;'>✦</span>
        </div>
        <h1 style='font-size:2.2rem;font-weight:900;color:#0f172a;margin:0 0 8px;letter-spacing:-1px;'>Nova Terminal</h1>
        <p style='color:#10b981;font-weight:800;font-size:0.9rem;margin:0;text-transform:uppercase;letter-spacing:2px;'>System Online</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Display chat messages
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            
    # Chat input
    if prompt := st.chat_input("Transmit query..."):
        with st.chat_message("user"):
            st.write(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                st.session_state.chat_history = nova_chat(
                    prompt, 
                    st.session_state.chat_history, 
                    st.session_state.uid, 
                    st.session_state.scan_st
                )
        st.rerun()

elif st.session_state.page == "profile":
    render_nav()
    st.markdown("""
    <div style='padding:10px 0;'>
        <h1 style='font-size:2.4rem;font-weight:900;color:#0f172a;margin:0 0 8px;letter-spacing:-1px;'>Identity Matrix</h1>
        <p style='color:#64748b;margin:0;font-weight:600;letter-spacing:1px;font-size:0.85rem;'>Current parameters.</p>
    </div>
    """, unsafe_allow_html=True)
    
    p = database.get_user_profile(st.session_state.uid) or {}
    if p:
        for k, v in p.items():
            if v:
                st.markdown(f"**{k.replace('_',' ').upper()}**")
                st.info(v)
    else:
        st.write("No data.")
        
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Modify Parameters", type="primary", use_container_width=True):
            navigate_to("onboarding")
    with col2:
        if st.button("Terminate Session", use_container_width=True):
            st.session_state.uid = ""
            st.session_state.username = ""
            st.session_state.scan_st = None
            st.session_state.chat_history = []
            navigate_to("splash")
