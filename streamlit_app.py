import streamlit as st
import json
import pymongo
import pandas as pd
from datetime import datetime, timedelta, timezone
from io import BytesIO
from fpdf import FPDF

# --- CUSTOM CSS FOR POLISHED INTERFACE ---
st.markdown("""
<style>
    /* Polish buttons and input alignments */
    div.stButton > button { height: 2.8em; padding-top: 0px; padding-bottom: 0px; font-size: 0.90rem; font-weight: 600; border-radius: 8px; }
    div.stNumberInput > div > div > input { height: 2.6em; text-align: center; font-size: 1.1rem; }
    
    /* Perfect column vertical alignment */
    [data-testid="column"] { display: flex; align-items: center; }

    /* SURGICAL CSS TO HIDE SPECIFIC CLOUD/TOOLBAR ELEMENTS ONLY */
    
    /* 1. Hide the Share / Deploy Button */
    .stDeployButton, [data-testid="stAppDeployButton"] { display: none !important; }
    
    /* 2. Hide the GitHub, Favorites, and Edit icons specifically (Leaves 3-dots menu alone) */
    [data-testid="stToolbarActionButton"] { display: none !important; }
    
    /* 3. Hide the Streamlit Community Cloud overlay badges (Removes "Manage app" and floating GitHub icons) */
    .viewerBadge_container__1QSob, 
    .styles_viewerBadge__1yB5_,
    .viewerBadge_link__1S137,
    .viewerBadge_text__1JaDK { display: none !important; }
    
    /* 4. Hide the standard Streamlit footer at the bottom */
    footer { display: none !important; }
</style>
""", unsafe_allow_html=True)

# --- CONFIGURATION ---
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

# --- DATABASE SETUP ---
@st.cache_resource
def get_mongo_client():
    uri = st.secrets["mongodb"]["uri"]
    return pymongo.MongoClient(uri, tls=True, serverSelectionTimeoutMS=5000, connectTimeoutMS=10000)

def load_db():
    try:
        client = get_mongo_client()
        db = client[st.secrets["mongodb"]["db_name"]]
        return {
            "participants": list(db.participants.find({}, {"_id": 0})),
            "fixtures": list(db.fixtures.find({}, {"_id": 0})),
            "predictions": list(db.predictions.find({}, {"_id": 0})),
            "teams": TEAMS
        }
    except Exception as e:
        st.error(f"Database Read Error: {e}")
        return {"participants": [], "fixtures": [], "predictions": [], "teams": TEAMS}

def save_db(data):
    try:
        client = get_mongo_client()
        db = client[st.secrets["mongodb"]["db_name"]]
        db.participants.delete_many({})
        if data.get("participants"): db.participants.insert_many([dict(p) for p in data["participants"]])
        db.fixtures.delete_many({})
        if data.get("fixtures"): db.fixtures.insert_many([dict(f) for f in data["fixtures"]])
        db.predictions.delete_many({})
        if data.get("predictions"): db.predictions.insert_many([dict(p) for p in data["predictions"]])
    except Exception as e:
        st.error(f"Database Write Error: {e}")

def get_flag(team): return FLAGS.get(team, "⚽")

def format_date(date_str):
    try: return datetime.strptime(date_str, "%Y-%m-%d").strftime("%a. %d %B")
    except: return date_str

def format_time(time_str):
    if not time_str: return "TBD"
    try: return datetime.strptime(time_str[:5], "%H:%M").strftime("%I:%M %p")
    except: return time_str

def compute_points(pred_A, pred_B, act_A, act_B):
    if act_A is None or act_B is None or pred_A is None or pred_B is None: return 0
    pA, pB, aA, aB = int(pred_A), int(pred_B), int(act_A), int(act_B)
    act_outcome = 1 if aA > aB else (2 if aA < aB else 0)
    pred_outcome = 1 if pA > pB else (2 if pA < pB else 0)
    if act_outcome == pred_outcome: return 4 if pA == aA and pB == aB else 3
    return 0

# --- USER PDF SUMMARY GENERATION ---
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
            pdf.cell(110, 10, match_str.encode('latin-1', 'replace').decode('latin-1'), border=1)
            pdf.cell(45, 10, pred_str, border=1, ln=True)
            
    return pdf.output(dest='S').encode('latin-1')

# --- START UP ---
st.set_page_config(layout="wide", page_title="WC2026 Dashboard")
db = load_db()
if "admin_authenticated" not in st.session_state: st.session_state.admin_authenticated = False
if "active_tab" not in st.session_state: st.session_state.active_tab = "Enter Scores"

st.image("assets/cover.jpg", use_container_width=True)

# --- SIDEBAR ADMIN AREA ---
show_admin_panel = False
with st.sidebar:
    st.title("🛡️ Admin Area")
    if not st.session_state.admin_authenticated:
        key = st.text_input("Admin Key", type="password")
        if st.button("Verify Key", use_container_width=True):
            if key == "admin123":
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
    col1, col2, col3, col4 = st.columns(4, gap="small")
    if col1.button("📝 Enter Scores", use_container_width=True, type="primary" if st.session_state.active_tab == "Enter Scores" else "secondary"):
        st.session_state.active_tab = "Enter Scores"; st.rerun()
    if col2.button("🏆 View Standings", use_container_width=True, type="primary" if st.session_state.active_tab == "View Standings" else "secondary"):
        st.session_state.active_tab = "View Standings"; st.rerun()
    if col3.button("📅 Upcoming Matches", use_container_width=True, type="primary" if st.session_state.active_tab == "Upcoming Matches" else "secondary"):
        st.session_state.active_tab = "Upcoming Matches"; st.rerun()
    if col4.button("📜 Rules", use_container_width=True, type="primary" if st.session_state.active_tab == "Rules" else "secondary"):
        st.session_state.active_tab = "Rules"; st.rerun()

    st.markdown("---")

    # -----------------------------------
    # VIEW: UPCOMING MATCHES
    # -----------------------------------
    if st.session_state.active_tab == "Upcoming Matches":
        st.subheader("Match Schedule")
        
        fixtures = db.get("fixtures", [])
        tab_pending, tab_finished = st.tabs(["⏳ Upcoming", "🟢 Finished"])
        
        with tab_pending:
            pending_fixtures = [f for f in fixtures if f.get("status") != "FINISHED"]
            
            if not pending_fixtures: 
                st.info("No upcoming matches scheduled.")
            else:
                # Using AST (UTC-4) for accurate local "Today" calculation
                ast_tz = timezone(timedelta(hours=-4))
                today_str = datetime.now(ast_tz).strftime("%Y-%m-%d")
                
                for f in pending_fixtures:
                    with st.container(border=True):
                        phase_text = f.get('phase', 'Group Stage')
                        time_text = format_time(f.get('time', ''))
                        
                        # Logic to check if the match date is 'Today' locally
                        if f.get('date') == today_str:
                            date_text = "🚨 :red[**TODAY**]"
                        else:
                            date_text = format_date(f.get('date', ''))
                            
                        st.caption(f"**{phase_text}** | {date_text} @ {time_text}")
                        st.markdown(f"{get_flag(f['teamA'])} **{f['teamA']}** vs **{f['teamB']}** {get_flag(f['teamB'])}")
                        
        with tab_finished:
            finished_fixtures = [f for f in fixtures if f.get("status") == "FINISHED"]
            if not finished_fixtures: 
                st.info("No matches have concluded yet.")
            else:
                for f in finished_fixtures:
                    with st.container(border=True):
                        st.caption(f"**{f.get('phase', 'Group Stage')}** | {format_date(f.get('date', ''))}")
                        res = f"{f.get('scoreA', 'N/A')}-{f.get('scoreB', 'N/A')}"
                        st.markdown(f"{get_flag(f['teamA'])} **{f['teamA']}** {res} **{f['teamB']}** {get_flag(f['teamB'])}")

    # -----------------------------------
    # VIEW: View Standings & PERFORMANCE MATRIX (MERGED)
    # -----------------------------------
    elif st.session_state.active_tab == "View Standings":
        participants = db.get("participants", [])
        fixtures = db.get("fixtures", [])
        predictions = db.get("predictions", [])
        
        if not participants or not fixtures:
            st.info("Data will populate once matches and participants are configured.")
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
                    pred = next((pr for pr in p_preds if pr["fixtureId"] == f["id"]), None)
                    
                    if pred is not None and pred.get("scoreA") is not None and pred.get("scoreB") is not None:
                        pred_str = f"{pred['scoreA']}-{pred['scoreB']}"
                        if is_finished:
                            pts = compute_points(pred["scoreA"], pred["scoreB"], f["scoreA"], f["scoreB"])
                            if pts == 4: exact_count += 1
                            if pts >= 3: outcome_count += 1
                            total_score += pts
                            match_breakdowns[match_header] = f"{pred_str} ({pts} pts)"
                        else: match_breakdowns[match_header] = pred_str
                    else: match_breakdowns[match_header] = "---"
                
                row_data.update({"Total Points": total_score, "Exact (4pt)": exact_count, "Outcome (3pt)": outcome_count})
                row_data.update(match_breakdowns)
                unified_data.append(row_data)
                
            df_unified = pd.DataFrame(unified_data).sort_values(by=["Total Points", "Exact (4pt)"], ascending=[False, False])
            
            # Leaderboard view with fixed numbering ranks
            df_leaderboard = df_unified[["Participant", "Total Points", "Exact (4pt)", "Outcome (3pt)"]].copy()
            df_leaderboard.insert(0, "Rank", range(1, len(df_leaderboard) + 1))
            
            st.dataframe(df_leaderboard, use_container_width=True, hide_index=True)

            # Export Excel Log
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_unified.to_excel(writer, index=False)
            st.download_button("📥 Download Excel Audit (.xlsx)", data=output.getvalue(), file_name="Tournament_Audit_Log.xlsx", mime="application/vnd.ms-excel", use_container_width=True)

            st.markdown("---")
            
            # Incorporated individual details lookup
            st.subheader("🔍 View Participant Predictions")
            selected_p_name = st.selectbox("Select a participant to view their full prediction list:", options=[p["name"] for p in participants])
            target_row = next((row for row in unified_data if row["Participant"] == selected_p_name), None)
            
            if target_row:
                with st.container(border=True):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Total Pts", target_row["Total Points"])
                    c2.metric("Exact Scores", target_row["Exact (4pt)"])
                    c3.metric("Correct Outcomes", target_row["Outcome (3pt)"])
                    st.divider()
                    for m_header in match_headers_list:
                        st.markdown(f"**{m_header}**: `{target_row[m_header]}`")
            
            st.markdown("---")
            
            # Incorporated global matrix expander
            with st.expander("📊 View Full Details (All Players vs All Matches)"):
                filter_matches = st.multiselect("Filter by Specific Matches:", options=match_headers_list, placeholder="Showing all matches...")
                df_filtered = df_unified.copy()
                if filter_matches:
                    keep_cols = ["Participant", "Total Points", "Exact (4pt)", "Outcome (3pt)"] + filter_matches
                    df_filtered = df_filtered[keep_cols]
                st.dataframe(df_filtered, use_container_width=True, hide_index=True)

    # -----------------------------------
    # VIEW: ENTER / SUBMIT SCORES & USER PDF SHEET
    # -----------------------------------
    elif st.session_state.active_tab == "Enter Scores":
        st.subheader("Submit Your Scores")
        participants = db.get("participants", [])
        participant_names = ["Select your name..."] + [p["name"] for p in participants]
        selected_name = st.selectbox("Who are you?", participant_names)
        
        if selected_name == "Select your name...":
            st.info("Please select your name above to unlock your prediction board.")
        else:
            participant = next((p for p in participants if p["name"] == selected_name), None)
            if participant:
                part_id = participant["id"]
                fixtures = db.get("fixtures", [])
                preds = db.get("predictions", [])
                
                # Using AST (UTC-4) for accurate local "Today" calculation
                ast_tz = timezone(timedelta(hours=-4))
                today_str = datetime.now(ast_tz).strftime("%Y-%m-%d")
                
                def get_existing_pred(fid): return next((p for p in preds if p["participantId"] == part_id and p["fixtureId"] == fid), None)

                # Generate and offer personal summary sheet PDF export
                user_preds = [p for p in preds if p["participantId"] == part_id]
                if user_preds:
                    pdf_data = generate_pdf_summary(selected_name, user_preds, fixtures)
                    st.download_button(
                        label="📥 Download Your Scores (PDF)",
                        data=pdf_data,
                        file_name=f"Predictions_{selected_name}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    st.write("")

                tab_pending, tab_locked = st.tabs(["⏳ Pending Matchups", "🟢 Locked Matchups"])
                
                with tab_pending:
                    # UPDATED: Only show pending matches if they haven't been predicted by the user yet
                    pending_fixtures = [f for f in fixtures if f.get("status") != "FINISHED" and get_existing_pred(f["id"]) is None]
                    if not pending_fixtures: st.info("No upcoming matches to predict.")
                    else:
                        for f in pending_fixtures:
                            curr_pred = get_existing_pred(f["id"])
                            # Logic for "TODAY" display locally
                            if f.get('date') == today_str:
                                date_text = "🚨 :red[**TODAY**]"
                            else:
                                date_text = format_date(f.get('date', ''))
                            
                            with st.container(border=True):
                                st.caption(f"**{f.get('phase', 'Group Stage')}** | {date_text} @ {format_time(f.get('time', ''))}")
                                
                                # Row 1: The Inputs
                                cols = st.columns([3, 1, 1])
                                cols[0].markdown(f"{get_flag(f['teamA'])} **{f['teamA']}** vs **{f['teamB']}** {get_flag(f['teamB'])}")
                                vA = cols[1].number_input(f"{f['teamA']}", 0, 20, int(curr_pred["scoreA"]) if curr_pred else 0, key=f"inpA_{f['id']}")
                                vB = cols[2].number_input(f"{f['teamB']}", 0, 20, int(curr_pred["scoreB"]) if curr_pred else 0, key=f"inpB_{f['id']}")
                                
                                # Row 2: Two-Step Confirmation logic
                                conf_cols = st.columns([2, 1])
                                # Included abbreviated names (first 3 letters) in the confirmation string
                                label_text = f"Confirm: **{f['teamA'][:3].upper()} {vA} - {vB} {f['teamB'][:3].upper()}**"
                                confirm_check = conf_cols[0].checkbox(label_text, key=f"chk_{f['id']}")
                                
                                if conf_cols[1].button("Save", key=f"btn_{f['id']}", disabled=not confirm_check, use_container_width=True, type="primary"):
                                    new_pred = {"participantId": part_id, "fixtureId": f["id"], "scoreA": vA, "scoreB": vB}
                                    db["predictions"] = [p for p in db["predictions"] if not (p["participantId"] == part_id and p["fixtureId"] == f["id"])] + [new_pred]
                                    save_db(db)
                                    st.toast(f"🎉 Prediction saved for {f['teamA']} vs {f['teamB']}!", icon="✅")
                                    st.rerun()

                with tab_locked:
                    # USERS CAN ONLY VIEW - NO EDITING TO PREVENT CHEATING
                    locked_fixtures = [f for f in fixtures if f.get("status") == "FINISHED" or get_existing_pred(f["id"]) is not None]
                    if locked_fixtures:
                        for f in locked_fixtures:
                            curr_pred = get_existing_pred(f["id"])
                            res = f"{curr_pred['scoreA']}-{curr_pred['scoreB']}" if curr_pred else "No prediction submitted"
                            st.markdown(f"{get_flag(f['teamA'])} **{f['teamA']}** vs **{f['teamB']}** {get_flag(f['teamB'])} | Your Selection: **{res}**")
                    else: st.info("No locked matches yet.")

    # -----------------------------------
    # VIEW: TOURNAMENT RULES & WA SHARING
    # -----------------------------------
    elif st.session_state.active_tab == "Rules":
        with st.container(border=True):
            st.markdown("### How to Play")
            st.markdown("- **3 Points:** For correctly predicting the right result (Win/Draw).")
            st.markdown("- **Bonus Point:** +1 bonus point for correctly predicting the exact score.")
            
            st.divider()
            
            st.markdown("### Instructions")
            st.markdown("1. **Submit:** Enter your predictions and click \"Save\".")
            st.markdown("2. **Download:** You can now download your scores in the 'Enter Scores' section.")
            st.markdown("3. **Track:** Check the 'View Standings' tab to see how you rank against others.")
            
            st.divider()
            
            st.markdown("### Cost")
            st.markdown("**$10 per game** (Pay Kevon).")
            
            st.divider()
            
            st.markdown("### Prize Distribution")
            st.markdown("- **1st Place:** 50% of the total funds collected.")
            st.markdown("- **2nd Place:** 30% of the total funds collected.")
            st.markdown("- **3rd Place:** 20% of the total funds collected.")
            
            st.divider()

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
                phase = st.text_input("Tournament Phase", "Group Stage")
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
                        db["fixtures"].append(new_fixture); save_db(db); st.success("Match Established!"); st.rerun()

        fixtures = db.get("fixtures", [])
        st.subheader("⏳ Pending Matches")
        for f in [f for f in fixtures if f["status"] == "PENDING"]:
            with st.container(border=True):
                st.markdown(f"**{f['phase']}** | {format_date(f['date'])}")
                cols = st.columns([3, 1, 1, 2])
                cols[0].markdown(f"**{get_flag(f['teamA'])} {f['teamA']} vs {f['teamB']} {get_flag(f['teamB'])}**")
                val_sa = cols[1].number_input(f"{f['teamA']}", 0, 20, f["scoreA"] or 0, key=f"sa_{f['id']}")
                val_sb = cols[2].number_input(f"{f['teamB']}", 0, 20, f["scoreB"] or 0, key=f"sb_{f['id']}")
                with cols[3]:
                    if st.button("✅ Finish", key=f"fin_{f['id']}", use_container_width=True):
                        f.update({"scoreA": val_sa, "scoreB": val_sb, "status": "FINISHED"})
                        save_db(db); st.rerun()

    elif admin_menu == "👥 Participants":
        st.title("👥 Registry")
        with st.form("enroll_player_form", clear_on_submit=True):
            new_player_name = st.text_input("Enter New Player Name:")
            if st.form_submit_button("Register Participant", use_container_width=True):
                if new_player_name.strip() != "":
                    db["participants"].append({"id": f"p_{int(datetime.now().timestamp())}", "name": new_player_name.strip()})
                    save_db(db); st.success(f"Enrolled!"); st.rerun()
        
        st.subheader("Current Roster")
        for p in db.get("participants", []):
            with st.container(border=True):
                c_name, c_delete = st.columns([3, 1])
                c_name.markdown(f"**{p['name']}**")
                if c_delete.button("🗑️ Del", key=f"del_{p['id']}", use_container_width=True):
                    db["participants"] = [x for x in db["participants"] if x["id"] != p["id"]]
                    db["predictions"] = [x for x in db["predictions"] if x["participantId"] != p["id"]]
                    save_db(db); st.rerun()
                    
    elif admin_menu == "📝 Edit Predictions":
        st.title("📝 Edit User Predictions")
        st.info("Use this tool to securely override a user's prediction if they made an error. Users cannot edit their own scores once saved.")
        
        participants = db.get("participants", [])
        fixtures = db.get("fixtures", [])
        preds = db.get("predictions", [])
        
        if not participants or not fixtures:
            st.warning("You need active participants and fixtures to use this tool.")
        else:
            sel_participant_name = st.selectbox("1. Select Participant", ["-- Select User --"] + [p["name"] for p in participants])
            
            if sel_participant_name != "-- Select User --":
                p_id = next(p["id"] for p in participants if p["name"] == sel_participant_name)
                
                match_options = ["-- Select Match --"] + [f"{f['teamA']} vs {f['teamB']} ({format_date(f['date'])})" for f in fixtures]
                sel_fixture_str = st.selectbox("2. Select Match", match_options)
                
                if sel_fixture_str != "-- Select Match --":
                    team_part = sel_fixture_str.split(" (")[0]
                    tA, tB = team_part.split(" vs ")
                    f_id = next(f["id"] for f in fixtures if f["teamA"] == tA and f["teamB"] == tB)
                    
                    curr_pred = next((p for p in preds if p["participantId"] == p_id and p["fixtureId"] == f_id), None)
                    
                    with st.container(border=True):
                        st.write(f"### Update: {tA} vs {tB}")
                        if curr_pred:
                            st.caption(f"Current prediction on file: **{curr_pred['scoreA']} - {curr_pred['scoreB']}**")
                        else:
                            st.caption("No prediction on file yet.")
                            
                        c1, c2 = st.columns(2)
                        new_sa = c1.number_input(f"{tA} Score", 0, 20, int(curr_pred["scoreA"]) if curr_pred else 0, key="ovr_A")
                        new_sb = c2.number_input(f"{tB} Score", 0, 20, int(curr_pred["scoreB"]) if curr_pred else 0, key="ovr_B")
                        
                        if st.button("🚨 Force Update Score", use_container_width=True, type="primary"):
                            new_pred = {"participantId": p_id, "fixtureId": f_id, "scoreA": new_sa, "scoreB": new_sb}
                            db["predictions"] = [p for p in db["predictions"] if not (p["participantId"] == p_id and p["fixtureId"] == f_id)] + [new_pred]
                            save_db(db)
                            st.success(f"Successfully updated prediction for {sel_participant_name}!")
                            st.rerun()

    elif admin_menu == "📥 Share & Export":
        st.title("📸 Database Engine Backup")
        st.info("Use this tab to download the complete latest JSON structure backup of your tournament ecosystem dataset data tables.")
        st.download_button(
            label="📥 Download System Backup (.json)",
            data=json.dumps(db, indent=4),
            file_name="system_data_backup.json",
            mime="application/json",
            use_container_width=True
        )