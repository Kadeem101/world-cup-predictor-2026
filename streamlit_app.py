import streamlit as st
import json
import hashlib
import pymongo
import pandas as pd
from datetime import datetime, timedelta, timezone
from io import BytesIO
from fpdf import FPDF
from streamlit_cookies_controller import CookieController
import time

# --- CUSTOM CSS FOR POLISHED INTERFACE ---
st.markdown("""
<style>
    /* Polish buttons and input alignments */
    div.stButton > button { height: 2.8em; padding-top: 0px; padding-bottom: 0px; font-size: 0.90rem; font-weight: 600; border-radius: 8px; }
    div.stNumberInput > div > div > input { height: 2.6em; text-align: center; font-size: 1.1rem; }
    
    /* Perfect column vertical alignment */
    [data-testid="column"] { display: flex; align-items: center; }

    /* SURGICAL CSS TO HIDE SPECIFIC CLOUD/TOOLBAR ELEMENTS ONLY */
    .stDeployButton, [data-testid="stAppDeployButton"] { display: none !important; }
    [data-testid="stToolbarActionButton"] { display: none !important; }
    .viewerBadge_container__1QSob, .styles_viewerBadge__1yB5_, .viewerBadge_link__1S137, .viewerBadge_text__1JaDK { display: none !important; }
    footer { display: none !important; }

    /* High-contrast Pill Badge for the Rules Button */
    div.stButton > button strong {
        background-color: #3c58fa;
        color: #ffffff;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.70rem;
        margin-left: 6px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
</style>
""", unsafe_allow_html=True)

# --- CONFIGURATION ---
MATCHES_PER_PAGE = 10

TEAMS = [
    "Algeria", "Argentina", "Australia", "Austria", "Belgium", "Bosnia and Herzegovina", 
    "Brazil", "Canada", "Cape Verde", "Colombia", "Croatia", "Curaçao", 
    "Czechia", "DR Congo", "Ecuador", "Egypt", "England", "France", 
    "Germany", "Ghana", "Haiti", "Iran", "Iraq", "Ivory Coast", "Japan", 
    "Jordan", "Mexico", "Morocco", "Netherlands", "New Zealand", "Norway", 
    "Panama", "Paraguay", "Portugal", "Qatar", "Saudi Arabia", "Scotland", 
    "Senegal", "South Africa", "South Korea", "Spain", "Sweden", 
    "Switzerland", "Tunisia", "Turkey", "USA", "Uruguay", "Uzbekistan"
]

FLAGS = {
    "Algeria": "![DZ](https://flagcdn.com/16x12/dz.png)", "Argentina": "![AR](https://flagcdn.com/16x12/ar.png)", 
    "Australia": "![AU](https://flagcdn.com/16x12/au.png)", "Austria": "![AT](https://flagcdn.com/16x12/at.png)", 
    "Belgium": "![BE](https://flagcdn.com/16x12/be.png)", "Bosnia and Herzegovina": "![BA](https://flagcdn.com/16x12/ba.png)", 
    "Brazil": "![BR](https://flagcdn.com/16x12/br.png)", "Canada": "![CA](https://flagcdn.com/16x12/ca.png)", 
    "Cape Verde": "![CV](https://flagcdn.com/16x12/cv.png)", "Colombia": "![CO](https://flagcdn.com/16x12/co.png)", 
    "Croatia": "![HR](https://flagcdn.com/16x12/hr.png)", "Curaçao": "![CW](https://flagcdn.com/16x12/cw.png)", 
    "Czechia": "![CZ](https://flagcdn.com/16x12/cz.png)", "DR Congo": "![CD](https://flagcdn.com/16x12/cd.png)", 
    "Ecuador": "![EC](https://flagcdn.com/16x12/ec.png)", "Egypt": "![EG](https://flagcdn.com/16x12/eg.png)", 
    "England": "![GB-ENG](https://flagcdn.com/16x12/gb-eng.png)", "France": "![FR](https://flagcdn.com/16x12/fr.png)", 
    "Germany": "![DE](https://flagcdn.com/16x12/de.png)", "Ghana": "![GH](https://flagcdn.com/16x12/gh.png)", 
    "Haiti": "![HT](https://flagcdn.com/16x12/ht.png)", "Iran": "![IR](https://flagcdn.com/16x12/ir.png)", 
    "Iraq": "![IQ](https://flagcdn.com/16x12/iq.png)", "Ivory Coast": "![CI](https://flagcdn.com/16x12/ci.png)", 
    "Japan": "![JP](https://flagcdn.com/16x12/jp.png)", "Jordan": "![JO](https://flagcdn.com/16x12/jo.png)", 
    "Mexico": "![MX](https://flagcdn.com/16x12/mx.png)", "Morocco": "![MA](https://flagcdn.com/16x12/ma.png)", 
    "Netherlands": "![NL](https://flagcdn.com/16x12/nl.png)", "New Zealand": "![NZ](https://flagcdn.com/16x12/nz.png)", 
    "Norway": "![NO](https://flagcdn.com/16x12/no.png)", "Panama": "![PA](https://flagcdn.com/16x12/pa.png)", 
    "Paraguay": "![PY](https://flagcdn.com/16x12/py.png)", "Portugal": "![PT](https://flagcdn.com/16x12/pt.png)", 
    "Qatar": "![QA](https://flagcdn.com/16x12/qa.png)", "Saudi Arabia": "![SA](https://flagcdn.com/16x12/sa.png)", 
    "Scotland": "![GB-SCT](https://flagcdn.com/16x12/gb-sct.png)", "Senegal": "![SN](https://flagcdn.com/16x12/sn.png)", 
    "South Africa": "![ZA](https://flagcdn.com/16x12/za.png)", "South Korea": "![KR](https://flagcdn.com/16x12/kr.png)", 
    "Spain": "![ES](https://flagcdn.com/16x12/es.png)", "Sweden": "![SE](https://flagcdn.com/16x12/se.png)", 
    "Switzerland": "![CH](https://flagcdn.com/16x12/ch.png)", "Tunisia": "![TN](https://flagcdn.com/16x12/tn.png)", 
    "Turkey": "![TR](https://flagcdn.com/16x12/tr.png)", "USA": "![US](https://flagcdn.com/16x12/us.png)", 
    "Uruguay": "![UY](https://flagcdn.com/16x12/uy.png)", "Uzbekistan": "![UZ](https://flagcdn.com/16x12/uz.png)"
}

# --- SURGICAL DATABASE FUNCTIONS (OPTIMIZED) ---
@st.cache_resource
def get_mongo_client():
    uri = st.secrets["mongodb"]["uri"]
    return pymongo.MongoClient(uri, tls=True, serverSelectionTimeoutMS=5000, connectTimeoutMS=10000)

@st.cache_data(ttl=30)  # 💡 NEW: Caches the database read for 30 seconds to prevent constant refreshing
def load_db():
    try:
        client = get_mongo_client()
        db = client[st.secrets["mongodb"]["db_name"]]
        return {
            "participants": list(db.participants.find({}, {"_id": 0})),
            "fixtures": list(db.fixtures.find({}, {"_id": 0}).sort([("date", 1), ("time", 1)])),
            "predictions": list(db.predictions.find({}, {"_id": 0})),
            "teams": TEAMS
        }
    except Exception as e:
        st.error(f"Database Read Error: {e}")
        return {"participants": [], "fixtures": [], "predictions": [], "teams": TEAMS}

# 💡 NEW: Targeted UPSERT / Delete functions instead of wipe-and-replace
def save_single_prediction(pred_data):
    try:
        db = get_mongo_client()[st.secrets["mongodb"]["db_name"]]
        db.predictions.update_one(
            {"participantId": pred_data["participantId"], "fixtureId": pred_data["fixtureId"]},
            {"$set": pred_data}, upsert=True
        )
    except Exception as e: st.error(f"DB Error: {e}")

def update_single_fixture(fixture_data):
    try:
        db = get_mongo_client()[st.secrets["mongodb"]["db_name"]]
        db.fixtures.update_one({"id": fixture_data["id"]}, {"$set": fixture_data}, upsert=True)
    except Exception as e: st.error(f"DB Error: {e}")

def delete_single_fixture(fixture_id):
    try:
        db = get_mongo_client()[st.secrets["mongodb"]["db_name"]]
        db.fixtures.delete_one({"id": fixture_id})
        db.predictions.delete_many({"fixtureId": fixture_id})
    except Exception as e: st.error(f"DB Error: {e}")

def update_single_participant(part_data):
    try:
        db = get_mongo_client()[st.secrets["mongodb"]["db_name"]]
        db.participants.update_one({"id": part_data["id"]}, {"$set": part_data}, upsert=True)
    except Exception as e: st.error(f"DB Error: {e}")

def delete_single_participant(part_id):
    try:
        db = get_mongo_client()[st.secrets["mongodb"]["db_name"]]
        db.participants.delete_one({"id": part_id})
        db.predictions.delete_many({"participantId": part_id})
    except Exception as e: st.error(f"DB Error: {e}")

def get_flag(team): return FLAGS.get(team, "⚽")

def flag_img_html(team, size="48x36"):
    md = FLAGS.get(team, "")
    if "(https://" in md:
        url = md.split("(")[1].rstrip(")").replace("16x12", size)
        return f'<img src="{url}" width="48" height="36" style="border-radius:3px;object-fit:cover;vertical-align:middle">'
    return '<span style="font-size:1.6rem;vertical-align:middle">⚽</span>'

def format_date(date_str):
    try: return datetime.strptime(date_str, "%Y-%m-%d").strftime("%a. %d %B")
    except: return date_str

def format_time(time_str):
    if not time_str: return "TBD"
    try: return datetime.strptime(time_str[:5], "%H:%M").strftime("%I:%M %p")
    except: return time_str

def make_auth_token(part_id, pin):
    return hashlib.sha256(f"{part_id}:{pin}:wc2026".encode()).hexdigest()[:20]

def compute_points(pred_A, pred_B, act_A, act_B, phase="Group Stage", pred_adv=None, act_adv=None, teamA=None, teamB=None):
    if act_A is None or act_B is None or pred_A is None or pred_B is None: return 0
    pA, pB, aA, aB = int(pred_A), int(pred_B), int(act_A), int(act_B)
    
    phase_clean = str(phase).lower().strip()
    
    base_outcome, exact_bonus = 3, 1
        
    act_outcome = 1 if aA > aB else (2 if aA < aB else 0)
    pred_outcome = 1 if pA > pB else (2 if pA < pB else 0)
    
    points = 0
    if act_outcome == pred_outcome:
        points += base_outcome
        if pA == aA and pB == aB:
            points += exact_bonus
            
    # 💡 NEW: Extract implicit advancing team if they predicted a 90-min win
    implied_pred_adv = pred_adv
    if not implied_pred_adv and teamA and teamB:
        if pA > pB: implied_pred_adv = teamA
        elif pB > pA: implied_pred_adv = teamB
            
    if "group" not in phase_clean and implied_pred_adv and act_adv and implied_pred_adv == act_adv:
        points += 1 # Eventual winner bonus
        
    return points

def generate_pdf_summary(name, predictions, fixtures):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "FIFA World Cup 2026 Predictions", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, f"Participant: {name}", ln=True)
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(110, 10, "Matchup", border=1)
    pdf.cell(45, 10, "Your Prediction", border=1, ln=True)
    
    pdf.set_font("Arial", size=11)
    for p in predictions:
        fix = next((f for f in fixtures if f["id"] == p["fixtureId"]), None)
        if fix:
            match_str = f"{fix['teamA']} vs {fix['teamB']}"
            pred_str = f"{p['scoreA']} - {p['scoreB']}"
            if p.get("advancedTeam"): pred_str += f" ({p['advancedTeam']} adv)"
            pdf.cell(110, 10, match_str.encode('latin-1', 'replace').decode('latin-1'), border=1)
            pdf.cell(45, 10, pred_str, border=1, ln=True)
            
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
#         START UP & GLOBAL DATA
# ==========================================
st.set_page_config(layout="wide", page_title="WC2026 Dashboard")

db = load_db()

participants = db.get("participants", [])
fixtures = db.get("fixtures", [])
predictions = db.get("predictions", [])

ast_tz = timezone(timedelta(hours=-4))
today_str = datetime.now(ast_tz).strftime("%Y-%m-%d")

if "admin_authenticated" not in st.session_state: st.session_state.admin_authenticated = False
if "active_tab" not in st.session_state: st.session_state.active_tab = "Enter Scores"
if "selected_name" not in st.session_state: st.session_state.selected_name = None
if "confirm_finish" not in st.session_state: st.session_state.confirm_finish = None
if "confirm_delete_fixture" not in st.session_state: st.session_state.confirm_delete_fixture = None
if "confirm_delete_participant" not in st.session_state: st.session_state.confirm_delete_participant = None
if "staged_pred" not in st.session_state: st.session_state.staged_pred = {}
if "verified_participant_id" not in st.session_state: st.session_state.verified_participant_id = None
if "auth_synced" not in st.session_state: st.session_state.auth_synced = False

cookie_controller = CookieController()

def _safe_cookie_get(name):
    # On a cold page load, the cookie component hasn't finished its
    # browser round-trip yet, so the controller's internal cache is still
    # None and .get() raises. Treat that brief window as "no cookie yet" --
    # the component will deliver the real value a moment later and trigger
    # an automatic rerun, at which point this will resolve normally.
    try:
        return cookie_controller.get(name)
    except TypeError:
        return None

_cpid = _safe_cookie_get("wc2026_pid")
_ctok = _safe_cookie_get("wc2026_tok")
_qpid = st.query_params.get("pid", "") or _cpid
_qtok = st.query_params.get("tok", "") or _ctok

if _qpid and _qtok and st.session_state.verified_participant_id != _qpid:
    _qpart = next((p for p in participants if p["id"] == _qpid), None)
    if _qpart:
        _qpin = str(_qpart.get("pin", "")).strip()
        if _qpin and _qtok == make_auth_token(_qpid, _qpin):
            st.session_state.verified_participant_id = _qpid
            st.session_state.selected_name = _qpart["name"]
            
            if (_cpid != _qpid or _ctok != _qtok) and not st.session_state.auth_synced:
                cookie_controller.set("wc2026_pid", _qpid, max_age=31536000)
                cookie_controller.set("wc2026_tok", _qtok, max_age=31536000)
                st.session_state.auth_synced = True

st.image("assets/cover.jpg", use_container_width=True)

# --- SIDEBAR ADMIN AREA ---
show_admin_panel = False
with st.sidebar:
    st.title("🛡️ Admin Area")
    if not st.session_state.admin_authenticated:
        key = st.text_input("Admin Key", type="password")
        if st.button("Verify Key", use_container_width=True):
            admin_key = st.secrets.get("admin", {}).get("key", "")
            if admin_key and key == admin_key:
                st.session_state.admin_authenticated = True
                st.success("Access Granted"); st.rerun()
            else: st.error("Invalid Key")
    else:
        if st.button("🚪 Close Session", use_container_width=True):
            st.session_state.admin_authenticated = False; st.rerun()
        st.divider()
        admin_menu = st.radio("Admin Actions", ["⬅️ Exit to Dashboard", "⚙️ Manage Games", "👥 Participants", "📝 Edit Predictions", "📥 Share & Export"])
        if admin_menu != "⬅️ Exit to Dashboard":
            show_admin_panel = True

# ==========================================
#         MAIN VIEW (USER INTERFACE)
# ==========================================
if not show_admin_panel:
    col1, col2, col3 = st.columns(3, gap="small")
    if col1.button("📝 Enter Scores", use_container_width=True, type="primary" if st.session_state.active_tab == "Enter Scores" else "secondary"):
        st.session_state.active_tab = "Enter Scores"; st.rerun()
    if col2.button("🏆 View Standings", use_container_width=True, type="primary" if st.session_state.active_tab == "View Standings" else "secondary"):
        st.session_state.active_tab = "View Standings"; st.rerun()
    if col3.button("📜 Rules **UPDATED**", use_container_width=True, type="primary" if st.session_state.active_tab == "Rules" else "secondary"):
        st.session_state.active_tab = "Rules"; st.rerun()

    st.markdown("---")

    # -----------------------------------
    # VIEW: View Standings
    # -----------------------------------
    if st.session_state.active_tab == "View Standings":
        if not participants or not fixtures:
            st.info("Data will populate once matches and participants are configured.")
        else:
            unified_data = []
            match_headers_list = []

            # 💡 NEW: Performance Fix (O(N^3) bottleneck eliminated via pre-calculation)
            pred_counts_by_fixture = {}
            for pr in predictions:
                pred_counts_by_fixture[pr["fixtureId"]] = pred_counts_by_fixture.get(pr["fixtureId"], 0) + 1

            for f in fixtures:
                is_finished = (f.get("status") == "FINISHED" and f.get("scoreA") is not None and f.get("scoreB") is not None)
                match_header = f"{f['teamA']} vs {f['teamB']} [{f['scoreA']}-{f['scoreB']}]" if is_finished else f"{f['teamA']} vs {f['teamB']} [Pending]"
                match_headers_list.append(match_header)

            for p in participants:
                total_score = 0
                exact_count = 0
                outcome_count = 0

                row_data = {"Participant": p["name"]}
                match_breakdowns = {}
                p_preds = [pr for pr in predictions if pr["participantId"] == p["id"]]

                for idx, f in enumerate(fixtures):
                    is_finished = (f.get("status") == "FINISHED" and f.get("scoreA") is not None and f.get("scoreB") is not None)
                    match_header = match_headers_list[idx]

                    # 💡 NEW: Lightning-fast lookup
                    fixture_all_entered = len(participants) > 0 and pred_counts_by_fixture.get(f["id"], 0) == len(participants)

                    pred = next((pr for pr in p_preds if pr["fixtureId"] == f["id"]), None)

                    if pred is not None and pred.get("scoreA") is not None and pred.get("scoreB") is not None:
                        pred_str = f"{pred['scoreA']}-{pred['scoreB']}"
                        pred_adv = pred.get("advancedTeam")

                        if is_finished:
                            pts = compute_points(
                                pred["scoreA"], pred["scoreB"], f["scoreA"], f["scoreB"], 
                                f.get("phase", "Group Stage"), pred_adv, f.get("advancedTeam"),
                                f["teamA"], f["teamB"]
                            )
                            
                            pA, pB, aA, aB = int(pred["scoreA"]), int(pred["scoreB"]), int(f["scoreA"]), int(f["scoreB"])
                            act_outcome = 1 if aA > aB else (2 if aA < aB else 0)
                            pred_outcome = 1 if pA > pB else (2 if pA < pB else 0)
                            
                            if act_outcome == pred_outcome:
                                outcome_count += 1
                                if pA == aA and pB == aB:
                                    exact_count += 1

                            total_score += pts

                            # 💡 NEW: Show who they picked to advance on knockout draws, with a
                            # ✅/❌ so it's clear any bonus point came from the advance pick,
                            # not from the scoreline being an exact match.
                            if pred_adv:
                                act_adv = f.get("advancedTeam")
                                adv_icon = "✅" if (act_adv and pred_adv == act_adv) else "❌"
                                pred_str += f" ➡️ {pred_adv} {adv_icon}"

                            match_breakdowns[match_header] = f"{pred_str} ({pts} pts)"
                        else:
                            if pred_adv:
                                pred_str += f" ➡️ {pred_adv}"
                            match_breakdowns[match_header] = pred_str if fixture_all_entered else "Score Submitted"
                    else:
                        match_breakdowns[match_header] = "---" if (is_finished or fixture_all_entered) else "No Score Yet"

                row_data.update({
                    "Points": total_score,
                    "Exact (1pt)": exact_count,
                    "Outcome (3pts)": outcome_count,
                })
                row_data.update(match_breakdowns)
                unified_data.append(row_data)

            df_unified = pd.DataFrame(unified_data).sort_values(by=["Points", "Exact (1pt)"], ascending=[False, False])

            # -----------------------------
            # Predefined Match Filtering Logic
            # -----------------------------
            with st.expander("⚙️ Filter Matches"):
                pending_matches = [m for i, m in enumerate(match_headers_list) if fixtures[i].get("status") != "FINISHED"]
                
                first_pending_idx = next((i for i, f in enumerate(fixtures) if f.get("status") != "FINISHED"), len(fixtures))
                WINDOW_SIZE = 10
                ideal_start = first_pending_idx - (WINDOW_SIZE // 2)
                max_start = max(0, len(fixtures) - WINDOW_SIZE)
                start_idx = max(0, min(ideal_start, max_start))
                end_idx = min(len(fixtures), start_idx + WINDOW_SIZE)
                intelligent_window = match_headers_list[start_idx:end_idx]

                preset_selection = st.radio(
                    "Choose a quick filter:",
                    options=["Default (last 10 matches)", "Pending Matches", "All Matches", "Custom Search"],
                    horizontal=True
                )

                if preset_selection == "Default (last 10 matches)": active_default = intelligent_window
                elif preset_selection == "Pending Matches": active_default = pending_matches
                elif preset_selection == "All Matches": active_default = match_headers_list
                else: active_default = []

                selected_matches = st.multiselect(
                    "🔍 Search or manually remove matches from the table:",
                    options=match_headers_list,
                    default=active_default,
                    placeholder="Type a team name to add a match...",
                    label_visibility="collapsed",
                    key=f"multiselect_{preset_selection}"
                )

            keep_cols = ["Participant", "Points", "Exact (1pt)", "Outcome (3pts)"] + selected_matches
            df_filtered = df_unified[keep_cols]
            df_filtered.insert(0, "Rank", range(1, len(df_filtered) + 1))

            def color_status(val):
                if val == "Score Submitted": return "color: #2ecc71"
                if val == "No Score Yet": return "color: #FF8C4A"
                return ""

            styled_df = df_filtered.style.map(color_status)
            st.dataframe(
                styled_df, use_container_width=True, hide_index=True,
                column_config={"Participant": st.column_config.Column(pinned=True), "Rank": st.column_config.Column(pinned=True)}
            )

            st.info("💡 **Note:** You'll only be able to view the other players' predictions once everyone enters their scores for that game.")

            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df_unified.to_excel(writer, index=False)

            st.download_button(
                "📥 Download Excel Audit (.xlsx)",
                data=output.getvalue(), file_name="Tournament_Audit_Log.xlsx",
                mime="application/vnd.ms-excel", use_container_width=True,
            )

    # -----------------------------------
    # VIEW: ENTER SCORES
    # -----------------------------------
    elif st.session_state.active_tab == "Enter Scores":
        st.subheader("Submit Your Scores")
        participant_names = [p["name"] for p in participants]

        selected_name = st.selectbox("Who are you?", options=participant_names, key="selected_name", placeholder="Select your name...")

        if not selected_name:
            st.info("Please select your name above to unlock your prediction board.")
        else:
            participant = next((p for p in participants if p["name"] == selected_name), None)
            if participant:
                part_id = participant["id"]

                # --- PIN VERIFICATION ---
                if st.session_state.verified_participant_id != part_id:
                    st.session_state.verified_participant_id = None
                    existing_pin = str(participant.get("pin", "")).strip()

                    with st.container(border=True):
                        if not existing_pin:
                            st.markdown("### 🔓 Create Your PIN")
                            st.caption("No PIN set. Create a private 4-digit PIN to protect your scores.")
                            new_pin_a = st.text_input("Choose a 4-digit PIN:", type="password", max_chars=4, key="pin_create_a")
                            new_pin_b = st.text_input("Confirm your PIN:", type="password", max_chars=4, key="pin_create_b")
                            if st.button("🔐 Set PIN & Unlock", use_container_width=True, type="primary"):
                                if not new_pin_a.strip().isdigit() or len(new_pin_a.strip()) != 4:
                                    st.error("⚠️ PIN must be exactly 4 digits (numbers only).")
                                elif new_pin_a.strip() != new_pin_b.strip():
                                    st.error("❌ PINs don't match. Please try again.")
                                else:
                                    participant["pin"] = new_pin_a.strip()
                                    update_single_participant(participant) # 💡 NEW: Upsert safe
                                    load_db.clear()
                                    
                                    auth_token = make_auth_token(part_id, new_pin_a.strip())
                                    st.session_state.verified_participant_id = part_id
                                    st.query_params["pid"] = part_id
                                    st.query_params["tok"] = auth_token
                                    cookie_controller.set("wc2026_pid", part_id, max_age=31536000)
                                    cookie_controller.set("wc2026_tok", auth_token, max_age=31536000)

                                    time.sleep(0.2)
                                    st.rerun()
                        else:
                            st.markdown("### 🔒 Enter Your PIN")
                            pin_input = st.text_input("4-digit PIN:", type="password", max_chars=4, key="pin_input")
                            if st.button("🔓 Unlock My Predictions", use_container_width=True, type="primary"):
                                if pin_input.strip() == existing_pin:
                                    auth_token = make_auth_token(part_id, pin_input.strip())
                                    st.session_state.verified_participant_id = part_id
                                    st.query_params["pid"] = part_id
                                    st.query_params["tok"] = auth_token
                                    cookie_controller.set("wc2026_pid", part_id, max_age=31536000)
                                    cookie_controller.set("wc2026_tok", auth_token, max_age=31536000)
                                    time.sleep(0.2)
                                    st.rerun()
                                else:
                                    st.error("❌ Incorrect PIN. Please try again.")
                    st.stop()

                # 💡 NEW: Performance Fix (O(N^2) Loop mapping)
                user_pred_map = {p["fixtureId"]: p for p in predictions if p["participantId"] == part_id}
                def get_existing_pred(fid): return user_pred_map.get(fid)

                total_fixtures = len(fixtures)
                predicted_count = sum(1 for f in fixtures if get_existing_pred(f["id"]) is not None)
                pending_count = len([f for f in fixtures if f.get("status") != "FINISHED" and get_existing_pred(f["id"]) is None])
                progress_pct = predicted_count / total_fixtures if total_fixtures > 0 else 0

                prog_col, stat_col = st.columns([3, 1])
                with prog_col: st.progress(progress_pct, text=f"**{predicted_count} of {total_fixtures}** matches predicted")
                with stat_col:
                    if pending_count > 0: st.warning(f"⚠️ {pending_count} still open", icon=None)
                    else: st.success("✅ All done for now!")
                st.write("")

                tab_pending, tab_schedule = st.tabs(["⏳ Pending Predictions", "📅 Full Schedule"])
                
                with tab_pending:
                    pending_fixtures = [f for f in fixtures if f.get("status") != "FINISHED" and get_existing_pred(f["id"]) is None]
                    if not pending_fixtures: st.info("No upcoming matches to predict.")
                    else:
                        for f in pending_fixtures:
                            curr_pred = get_existing_pred(f["id"])
                            date_text = "🚨 :red[**TODAY**]" if f.get('date') == today_str else format_date(f.get('date', ''))

                            with st.container(border=True):
                                st.caption(f"**{f.get('phase', 'Group Stage')}** | {date_text} @ {format_time(f.get('time', ''))}")

                                if f["id"] in st.session_state.staged_pred:
                                    staged_data = st.session_state.staged_pred[f["id"]]
                                    sA, sB = staged_data[0], staged_data[1]
                                    adv_team = staged_data[2] if len(staged_data) > 2 else None

                                    if sA > sB:   outcome = f"🏆 {f['teamA']} Win in 90 mins"
                                    elif sB > sA: outcome = f"🏆 {f['teamB']} Win in 90 mins"
                                    else:         
                                        outcome = "🤝 Draw at 90 mins"
                                        if adv_team: outcome += f" ➡️ **{adv_team} Advances**"

                                    st.markdown(f"""
<div style="padding:4px 0 8px 0">
    <div style="display:flex;align-items:center;padding:10px 4px;border-bottom:1px solid rgba(128,128,128,0.25)">
        {flag_img_html(f['teamA'])}
        <span style="flex:1;font-size:1.05rem;font-weight:600;margin-left:12px">{f['teamA']}</span>
        <span style="font-size:2rem;font-weight:800;min-width:32px;text-align:right">{sA}</span>
    </div>
    <div style="display:flex;align-items:center;padding:10px 4px">
        {flag_img_html(f['teamB'])}
        <span style="flex:1;font-size:1.05rem;font-weight:600;margin-left:12px">{f['teamB']}</span>
        <span style="font-size:2rem;font-weight:800;min-width:32px;text-align:right">{sB}</span>
    </div>
</div>
""", unsafe_allow_html=True)

                                    st.caption(f"Predicted result: {outcome}")

                                    if sA == 0 and sB == 0 and not adv_team:
                                        st.warning("⚠️ You're predicting a **0 – 0 draw** — is that intentional?")

                                    rev_cols = st.columns(2)
                                    if rev_cols[0].button("✏️ Edit", key=f"edit_{f['id']}", use_container_width=True):
                                        del st.session_state.staged_pred[f["id"]]
                                        st.rerun()
                                    if rev_cols[1].button("✅ Confirm & Save", key=f"confirm_{f['id']}", use_container_width=True, type="primary"):
                                        new_pred = {"participantId": part_id, "fixtureId": f["id"], "scoreA": sA, "scoreB": sB}
                                        if adv_team: new_pred["advancedTeam"] = adv_team
                                        
                                        # 💡 NEW: Upsert safe save and cache clear
                                        save_single_prediction(new_pred)
                                        load_db.clear()
                                        
                                        del st.session_state.staged_pred[f["id"]]
                                        st.toast(f"🎉 Prediction saved for {f['teamA']} vs {f['teamB']}!", icon="✅")
                                        st.rerun()

                                else:
                                    cols = st.columns([3, 1, 1])
                                    cols[0].markdown(f"{get_flag(f['teamA'])} **{f['teamA']}** vs **{f['teamB']}** {get_flag(f['teamB'])}")
                                    vA = cols[1].number_input(f"{f['teamA']}", 0, 20, int(curr_pred["scoreA"]) if curr_pred else 0, key=f"inpA_{f['id']}")
                                    vB = cols[2].number_input(f"{f['teamB']}", 0, 20, int(curr_pred["scoreB"]) if curr_pred else 0, key=f"inpB_{f['id']}")

                                    adv_team = None
                                    if f.get('phase', 'Group Stage').lower() != "group stage" and vA == vB:
                                        curr_adv = curr_pred.get("advancedTeam") if curr_pred else None
                                        adv_options = [f['teamA'], f['teamB']]
                                        adv_idx = adv_options.index(curr_adv) if curr_adv in adv_options else 0
                                        adv_team = st.selectbox("🤝 Match tied after 90 mins! - Choose who wins via Extra-Time/Penalties:", adv_options, index=adv_idx, key=f"adv_{f['id']}")

                                    if st.button("👁️ Preview Prediction", key=f"btn_{f['id']}", use_container_width=True):
                                        st.session_state.staged_pred[f["id"]] = (vA, vB, adv_team)
                                        st.rerun()

                    user_preds = [p for p in predictions if p["participantId"] == part_id]
                    if user_preds:
                        st.divider()
                        pdf_data = generate_pdf_summary(selected_name, user_preds, fixtures)
                        st.download_button(
                            label="📥 Download Your Predictions (PDF)",
                            data=pdf_data, file_name=f"Predictions_{selected_name}.pdf",
                            mime="application/pdf", use_container_width=True, key="pdf_download_pending"
                        )

                with tab_schedule:
                    search_sched = st.text_input("🔍 Filter by team...", key="search_schedule").lower()
                    all_sorted = sorted(fixtures, key=lambda f: (f.get("date", ""), f.get("time", "")))
                    filtered_sched = [f for f in all_sorted if search_sched in f['teamA'].lower() or search_sched in f['teamB'].lower()] if search_sched else all_sorted
                    if not filtered_sched:
                        st.info("No matches found.")
                    else:
                        with st.container(height=450, border=False):
                            for f in filtered_sched:
                                with st.container(border=True):
                                    status = f.get("status", "PENDING")
                                    if status == "FINISHED":
                                        res = f"{f.get('scoreA', '?')}-{f.get('scoreB', '?')}"
                                        curr_pred = get_existing_pred(f["id"])
                                        my_pred = f"| Your Pick: **{curr_pred['scoreA']}-{curr_pred['scoreB']}**" if curr_pred else "| No prediction"
                                        st.caption(f"**{f.get('phase', 'Group Stage')}** | {format_date(f.get('date', ''))} ✅ Done")
                                        st.markdown(f"{get_flag(f['teamA'])} **{f['teamA']}** {res} **{f['teamB']}** {get_flag(f['teamB'])} {my_pred}")
                                    else:
                                        date_text = "🚨 :red[**TODAY**]" if f.get('date') == today_str else format_date(f.get('date', ''))
                                        curr_pred = get_existing_pred(f["id"])
                                        my_pred = f"| Your Pick: **{curr_pred['scoreA']}-{curr_pred['scoreB']}**" if curr_pred else "| ⏳ Awaiting prediction"
                                        st.caption(f"**{f.get('phase', 'Group Stage')}** | {date_text} @ {format_time(f.get('time', ''))}")
                                        st.markdown(f"{get_flag(f['teamA'])} **{f['teamA']}** vs **{f['teamB']}** {get_flag(f['teamB'])} {my_pred}")

    # -----------------------------------
    # VIEW: TOURNAMENT RULES 
    # -----------------------------------
    elif st.session_state.active_tab == "Rules":
        with st.container(border=True):
            st.markdown("### Scoring Rules")
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown("#### Group Stage")
                st.markdown("""
                * **Correct Outcome:** 3 pts *(Win / Draw)*
                * **Exact Score:** +1 pt bonus
                * **Max Points:** **4 pts per match**
                """)
                
            with c2:
                st.markdown("#### Knockout Stage")
                st.markdown("""
                * **Correct Outcome:** 3 pts *(Win / Draw after 90-Min)*
                * **Exact Score:** +1 pt bonus *(After 90-Min)*
                * **Winner Bonus:** +1 pt bonus
                  *(Only awarded if you predict a Draw after 90-Min and correctly guess who wins via ET/Penalties.)*
                * **Max Points:** **5 pts per match**
                """)
            
            st.divider()
            
            c3, c4 = st.columns(2)
            with c3:
                st.markdown("#### Cost & Prize Distribution")
                st.markdown("""
                104 games - $10 per game (Pay Kevon)
                * **1st Place:** 50% of total funds
                * **2nd Place:** 30% of total funds
                * **3rd Place:** 20% of total funds
                """)
            with c4:
                st.markdown("#### Instructions")
                st.markdown("""
                1. Enter Scores.
                2. Confirm and Save scores.
                3. Download scores.
                
                """)

# ==========================================
#         ADMIN VIEW PANEL CONTROLLERS
# ==========================================
if show_admin_panel:
    st.info("You are currently viewing the Admin Console.")
    
    if admin_menu == "⚙️ Manage Games":
        st.title("⚙️ Match Controller")
        with st.expander("➕ Create New Match", expanded=False):
            with st.form("add_new_fixture_form"):
                teamA = st.selectbox("Home Team", sorted(TEAMS))
                teamB = st.selectbox("Away Team", sorted(TEAMS))

                TOURNAMENT_PHASES = ["Group Stage", "Round of 32", "Round of 16", "Quarterfinals", "Semifinals", "Third place play-off", "Final"]
                phase = st.selectbox("Tournament Phase", TOURNAMENT_PHASES, index=0)
                date_val = st.date_input("Scheduled Date")
                
                col_h, col_m, col_p = st.columns([1, 1, 1])
                hr_val = col_h.selectbox("Hour", ["12", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11"], index=3)
                min_val = col_m.selectbox("Minute", ["00", "15", "30", "45"])
                ampm_val = col_p.selectbox("AM/PM", ["AM", "PM"], index=1)
                
                if st.form_submit_button("Generate Match", use_container_width=True):
                    if teamA == teamB: st.error("Invalid Matching: Teams must be different.")
                    else:
                        h_int = int(hr_val)
                        if ampm_val == "PM" and h_int != 12: h_int += 12
                        elif ampm_val == "AM" and h_int == 12: h_int = 0
                        new_fixture = {
                            "id": f"f_{int(datetime.now().timestamp())}", "teamA": teamA, "teamB": teamB,
                            "date": str(date_val), "time": f"{h_int:02d}:{min_val}", "phase": phase, 
                            "scoreA": None, "scoreB": None, "status": "PENDING"
                        }
                        # 💡 NEW: Upsert safe save
                        update_single_fixture(new_fixture)
                        load_db.clear()
                        st.success("Match Established!"); st.rerun()

        st.subheader("⏳ Pending Matches")
        pending_fixtures = [f for f in fixtures if f["status"] == "PENDING"]
        if not pending_fixtures: st.info("No pending matches.")
        for f in pending_fixtures:
            with st.container(border=True):
                st.markdown(f"**{f['phase']}** | {format_date(f['date'])} @ {format_time(f['time'])}")
                cols = st.columns([3, 1, 1, 1, 1])
                cols[0].markdown(f"**{get_flag(f['teamA'])} {f['teamA']} vs {f['teamB']} {get_flag(f['teamB'])}**")
                val_sa = cols[1].number_input(f"{f['teamA']}", 0, 20, f["scoreA"] or 0, key=f"sa_{f['id']}")
                val_sb = cols[2].number_input(f"{f['teamB']}", 0, 20, f["scoreB"] or 0, key=f"sb_{f['id']}")

                admin_adv_team = None
                if f.get('phase', 'Group Stage').lower() != "group stage" and val_sa == val_sb:
                    admin_adv_team = st.selectbox("⚖️ Match drawn at 90 mins! Who advanced?", [f['teamA'], f['teamB']], key=f"admin_adv_{f['id']}")

                with cols[3]:
                    if st.session_state.confirm_finish == f["id"]:
                        if st.button("✅ Confirm", key=f"conf_fin_{f['id']}", use_container_width=True, type="primary"):
                            update_payload = {"id": f["id"], "scoreA": val_sa, "scoreB": val_sb, "status": "FINISHED"}
                            if admin_adv_team: update_payload["advancedTeam"] = admin_adv_team
                            
                            # 💡 NEW: Upsert safe
                            update_single_fixture(update_payload)
                            load_db.clear()
                            
                            st.session_state.confirm_finish = None
                            st.rerun()
                    # Add this missing else block below to trigger the confirm state
                    else:
                        if st.button("🏁 Finish", key=f"init_fin_{f['id']}", use_container_width=True):
                            st.session_state.confirm_finish = f["id"]
                            st.rerun()
                with cols[4]:
                    if st.session_state.confirm_delete_fixture == f["id"]:
                        if st.button("🗑️ Confirm", key=f"conf_del_fix_{f['id']}", use_container_width=True, type="primary"):
                            delete_single_fixture(f["id"])
                            load_db.clear()
                            st.session_state.confirm_delete_fixture = None
                            st.rerun()
                    else:
                        if st.button("🗑️ Delete", key=f"del_fix_{f['id']}", use_container_width=True):
                            st.session_state.confirm_delete_fixture = f["id"]; st.rerun()

                if st.session_state.confirm_finish == f["id"]: st.warning(f"⚠️ Confirm finishing **{f['teamA']} {val_sa} – {val_sb} {f['teamB']}**? This locks all predictions.")
                elif st.session_state.confirm_delete_fixture == f["id"]: st.warning(f"⚠️ Confirm deleting **{f['teamA']} vs {f['teamB']}**? All predictions for this match will also be removed.")

        st.divider()
        st.subheader("✅ Finished Matches")
        finished_fixtures = [f for f in fixtures if f["status"] == "FINISHED"]
        if not finished_fixtures: st.info("No finished matches yet.")
        for f in finished_fixtures:
            with st.container(border=True):
                cols = st.columns([4, 1])
                cols[0].markdown(f"**{f['phase']}** | {format_date(f['date'])} — {get_flag(f['teamA'])} **{f['teamA']}** {f['scoreA']}–{f['scoreB']} **{f['teamB']}** {get_flag(f['teamB'])}")
                with cols[1]:
                    if st.session_state.confirm_delete_fixture == f["id"]:
                        if st.button("🗑️ Confirm", key=f"conf_del_fin_{f['id']}", use_container_width=True, type="primary"):
                            delete_single_fixture(f["id"])
                            load_db.clear()
                            st.session_state.confirm_delete_fixture = None
                            st.rerun()
                    else:
                        if st.button("🗑️ Delete", key=f"del_fin_{f['id']}", use_container_width=True):
                            st.session_state.confirm_delete_fixture = f["id"]; st.rerun()
                if st.session_state.confirm_delete_fixture == f["id"]: st.warning(f"⚠️ Confirm deleting **{f['teamA']} vs {f['teamB']}**? All predictions for this match will also be removed.")

    elif admin_menu == "👥 Participants":
        st.title("👥 Registry")
        with st.form("enroll_player_form", clear_on_submit=True):
            new_player_name = st.text_input("Enter New Player Name:")
            new_player_pin = st.text_input("PIN (optional):", max_chars=4, help="Leave blank to let the participant set their own PIN on first login.")
            if st.form_submit_button("Register Participant", use_container_width=True):
                if new_player_name.strip() != "":
                    pin_value = new_player_pin.strip()
                    if pin_value and (not pin_value.isdigit() or len(pin_value) != 4): st.error("PIN must be exactly 4 digits (numbers only), or leave it blank.")
                    else:
                        new_p = {"id": f"p_{int(datetime.now().timestamp())}", "name": new_player_name.strip()}
                        if pin_value: new_p["pin"] = pin_value
                        update_single_participant(new_p)
                        load_db.clear()
                        st.success(f"Enrolled!"); st.rerun()
        
        st.subheader("Current Roster")
        for p in participants:
            with st.container(border=True):
                c_name, c_delete = st.columns([3, 1])
                pred_count = len([x for x in predictions if x["participantId"] == p["id"]])
                current_pin = p.get("pin", None)
                pin_display = f"`{current_pin}`" if current_pin else "⚠️ *Not set*"
                c_name.markdown(f"**{p['name']}** — {pred_count} prediction{'s' if pred_count != 1 else ''} on file | 🔑 PIN: {pin_display}")
                with c_delete:
                    if st.session_state.confirm_delete_participant == p["id"]:
                        if st.button("🗑️ Confirm", key=f"conf_del_p_{p['id']}", use_container_width=True, type="primary"):
                            delete_single_participant(p["id"])
                            load_db.clear()
                            st.session_state.confirm_delete_participant = None
                            st.rerun()
                    else:
                        if st.button("🗑️ Del", key=f"del_{p['id']}", use_container_width=True):
                            st.session_state.confirm_delete_participant = p["id"]; st.rerun()
                c_pin_input, c_pin_btn = st.columns([3, 1])
                new_pin = c_pin_input.text_input("Reset PIN", max_chars=4, key=f"new_pin_{p['id']}", label_visibility="collapsed", placeholder="Type new 4-digit PIN to reset...")
                if c_pin_btn.button("🔑 Set PIN", key=f"update_pin_{p['id']}", use_container_width=True):
                    if new_pin.strip().isdigit() and len(new_pin.strip()) == 4:
                        p["pin"] = new_pin.strip()
                        update_single_participant(p)
                        load_db.clear()
                        st.success(f"✅ PIN updated for **{p['name']}**!"); st.rerun()
                    else: st.error("⚠️ PIN must be exactly 4 digits.")
                if st.session_state.confirm_delete_participant == p["id"]: st.warning(f"⚠️ Confirm removing **{p['name']}**? This will permanently delete them and all {pred_count} of their predictions.")
                    
    elif admin_menu == "📝 Edit Predictions":
        st.title("📝 Edit User Predictions")
        st.info("Use this tool to securely override a user's prediction if they made an error. Users cannot edit their own scores once saved.")
        
        if not participants or not fixtures: st.warning("You need active participants and fixtures to use this tool.")
        else:
            sel_participant_name = st.selectbox("1. Select Participant", ["-- Select User --"] + [p["name"] for p in participants])
            
            if sel_participant_name != "-- Select User --":
                p_id = next((p["id"] for p in participants if p["name"] == sel_participant_name), None)
                if not p_id: st.error("Participant not found. Please refresh and try again."); st.stop()
                
                def fixture_label(f):
                    status_tag = "✅ Final" if f["status"] == "FINISHED" else "⏳ Pending"
                    return f"{f['teamA']} vs {f['teamB']} ({format_date(f['date'])}) [{status_tag}]"
                
                match_options = ["-- Select Match --"] + [fixture_label(f) for f in fixtures]
                sel_fixture_str = st.selectbox("2. Select Match", match_options)
                
                if sel_fixture_str != "-- Select Match --":
                    f_obj = next((f for f in fixtures if fixture_label(f) == sel_fixture_str), None)
                    if f_obj:
                        f_id = f_obj["id"]
                        tA, tB = f_obj["teamA"], f_obj["teamB"]
                        curr_pred = next((p for p in predictions if p["participantId"] == p_id and p["fixtureId"] == f_id), None)
                        
                        with st.container(border=True):
                            st.write(f"### Update: {tA} vs {tB}")
                            if f_obj["status"] == "FINISHED": st.caption(f"✅ Final score: **{f_obj['scoreA']} – {f_obj['scoreB']}**")
                            if curr_pred: st.caption(f"Current prediction on file: **{curr_pred['scoreA']} - {curr_pred['scoreB']}**")
                            else: st.caption("No prediction on file yet.")
                                
                            c1, c2 = st.columns(2)
                            new_sa = c1.number_input(f"{tA} Score", 0, 20, int(curr_pred["scoreA"]) if curr_pred else 0, key="ovr_A")
                            new_sb = c2.number_input(f"{tB} Score", 0, 20, int(curr_pred["scoreB"]) if curr_pred else 0, key="ovr_B")
                            
                            if st.button("🚨 Force Update Score", use_container_width=True, type="primary"):
                                new_pred = {"participantId": p_id, "fixtureId": f_id, "scoreA": new_sa, "scoreB": new_sb}
                                save_single_prediction(new_pred)
                                load_db.clear()
                                st.success(f"Successfully updated prediction for {sel_participant_name}!")
                                st.rerun()

    elif admin_menu == "📥 Share & Export":
        st.title("📥 Share & Export")

        st.subheader("📊 Excel Audit Report")
        if not participants or not fixtures: st.info("No data available to export yet.")
        else:
            unified_data = []
            match_headers_list = []
            for f in fixtures:
                is_finished = f.get("status") == "FINISHED" and f.get("scoreA") is not None and f.get("scoreB") is not None
                match_header = f"{f['teamA']} vs {f['teamB']} [{f['scoreA']}-{f['scoreB']}]" if is_finished else f"{f['teamA']} vs {f['teamB']} [Pending]"
                match_headers_list.append(match_header)
            for p in participants:
                total_score, exact_count, outcome_count = 0, 0, 0
                row_data = {"Participant": p["name"]}
                match_breakdowns = {}
                p_preds = [pr for pr in predictions if pr["participantId"] == p["id"]]
                for idx, f in enumerate(fixtures):
                    is_finished = f.get("status") == "FINISHED" and f.get("scoreA") is not None and f.get("scoreB") is not None
                    match_header = match_headers_list[idx]
                    
                    fixture_all_entered = (len(participants) > 0) and sum(1 for pr in predictions if pr["fixtureId"] == f["id"]) == len(participants)
                    
                    pred = next((pr for pr in p_preds if pr["fixtureId"] == f["id"]), None)
                    if pred is not None and pred.get("scoreA") is not None and pred.get("scoreB") is not None:
                        pred_str = f"{pred['scoreA']}-{pred['scoreB']}"
                        pred_adv = pred.get("advancedTeam")
                        if is_finished:
                            pts = compute_points(
                                pred["scoreA"], pred["scoreB"], f["scoreA"], f["scoreB"], 
                                f.get("phase", "Group Stage"), pred_adv, f.get("advancedTeam"), 
                                f["teamA"], f["teamB"]
                            )
                            pA, pB, aA, aB = int(pred["scoreA"]), int(pred["scoreB"]), int(f["scoreA"]), int(f["scoreB"])
                            act_outcome = 1 if aA > aB else (2 if aA < aB else 0)
                            pred_outcome = 1 if pA > pB else (2 if pA < pB else 0)
                            
                            if act_outcome == pred_outcome:
                                outcome_count += 1
                                if pA == aA and pB == aB: exact_count += 1
                                    
                            total_score += pts
                            if pred_adv:
                                act_adv = f.get("advancedTeam")
                                adv_icon = "✅" if (act_adv and pred_adv == act_adv) else "❌"
                                pred_str += f" ➡️ {pred_adv} {adv_icon}"
                            match_breakdowns[match_header] = f"{pred_str} ({pts} pts)"
                        else:
                            if pred_adv:
                                pred_str += f" ➡️ {pred_adv}"
                            match_breakdowns[match_header] = pred_str if fixture_all_entered else "Score Submitted"
                    else: match_breakdowns[match_header] = "---" if (is_finished or fixture_all_entered) else "No Score Yet"
                row_data.update({"Points": total_score, "Exact (1pt)": exact_count, "Outcome (3pts)": outcome_count})
                row_data.update(match_breakdowns)
                unified_data.append(row_data)
            df_export = pd.DataFrame(unified_data).sort_values(by=["Points", "Exact (1pt)"], ascending=[False, False])
            df_export.insert(0, "Rank", range(1, len(df_export) + 1))
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_export.to_excel(writer, index=False)
            st.download_button(
                label="📥 Download Excel Audit (.xlsx)", data=output.getvalue(),
                file_name="Tournament_Audit_Log.xlsx", mime="application/vnd.ms-excel",
                use_container_width=True, key="admin_excel_export"
            )

        st.divider()
        st.subheader("🗄️ Database Backup")
        st.caption("Raw JSON backup of all participants, fixtures, and predictions.")
        st.download_button(
            label="📥 Download System Backup (.json)", data=json.dumps(db, indent=4),
            file_name="system_data_backup.json", mime="application/json",
            use_container_width=True, key="admin_json_export"
        )