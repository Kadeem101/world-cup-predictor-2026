import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
from io import BytesIO

# Database Path
DB_FILE = "data.json"

# --- CONFIGURATION: 48 WORLD CUP TEAMS & FLAGS ---
TEAMS = [
    "Argentina", "Australia", "Austria", "Belgium", "Bosnia and Herzegovina", 
    "Brazil", "Canada", "Cape Verde", "Colombia", "Croatia", "Curaçao", 
    "Czechia", "DR Congo", "Ecuador", "Egypt", "England", "France", 
    "Germany", "Ghana", "Haiti", "Iran", "Iraq", "Ivory Coast", "Japan", 
    "Jordan", "Mexico", "Morocco", "Netherlands", "New Zealand", "Norway", 
    "Panama", "Paraguay", "Portugal", "Qatar", "Saudi Arabia", "Scotland", 
    "Senegal", "South Africa", "South Korea", "Spain", "Sweden", 
    "Switzerland", "Tunisia", "Turkey", "USA", "Uruguay", "Uzbekistan"
]

FLAGS = {
    "Argentina": "🇦🇷", "Australia": "🇦🇺", "Austria": "🇦🇹", "Belgium": "🇧🇪",
    "Bosnia and Herzegovina": "🇧🇦", "Brazil": "🇧🇷", "Canada": "🇨🇦", "Cape Verde": "🇨🇻",
    "Colombia": "🇨🇴", "Croatia": "🇭🇷", "Curaçao": "🇨🇼", "Czechia": "🇨🇿",
    "DR Congo": "🇨🇩", "Ecuador": "🇪🇨", "Egypt": "🇪🇬", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "France": "🇫🇷", "Germany": "🇩🇪", "Ghana": "🇬🇭", "Haiti": "🇭🇹",
    "Iran": "🇮🇷", "Iraq": "🇮🇶", "Ivory Coast": "🇨🇮", "Japan": "🇯🇵",
    "Jordan": "🇯🇴", "Mexico": "🇲🇽", "Morocco": "🇲🇦", "Netherlands": "🇳🇱",
    "New Zealand": "🇳🇿", "Norway": "🇳🇴", "Panama": "🇵🇦", "Paraguay": "🇵🇾",
    "Portugal": "🇵🇹", "Qatar": "🇶🇦", "Saudi Arabia": "🇸🇦", "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "Senegal": "🇸🇳", "South Africa": "🇿🇦", "South Korea": "🇰🇷", "Spain": "🇪🇸",
    "Sweden": "🇸🇪", "Switzerland": "🇨🇭", "Tunisia": "🇹🇳", "Turkey": "🇹🇷",
    "USA": "🇺🇸", "Uruguay": "🇺🇾", "Uzbekistan": "🇺🇿"
}

def get_flag(team):
    return FLAGS.get(team, "⚽")

def format_time(time_str):
    if not time_str: return "TBD"
    try:
        return datetime.strptime(time_str[:5], "%H:%M").strftime("%I:%M %p")
    except Exception:
        return time_str

# --- DATABASE LOGIC ---
def load_db():
    if not os.path.exists(DB_FILE):
        return {"participants": [], "fixtures": [], "predictions": [], "teams": TEAMS}
    with open(DB_FILE, "r") as f:
        data = json.load(f)
        if "teams" not in data:
            data["teams"] = TEAMS
        return data

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- NEW SCORING COMPUTATION ---
def compute_points(pred_A, pred_B, act_A, act_B):
    if act_A is None or act_B is None or pred_A is None or pred_B is None:
        return 0
    
    pA, pB = int(pred_A), int(pred_B)
    aA, aB = int(act_A), int(act_B)
    
    # 1 for Team A win, 2 for Team B win, 0 for draw
    act_outcome = 1 if aA > aB else (2 if aA < aB else 0)
    pred_outcome = 1 if pA > pB else (2 if pA < pB else 0)
    
    if act_outcome == pred_outcome:
        # 3 points for correct outcome, plus 1 extra point for exact score (Total: 4)
        if pA == aA and pB == aB:
            return 4
        return 3 # 3 points for correct outcome only
    
    return 0

# --- START UP ---
st.set_page_config(page_title="WC2026 Dashboard", layout="wide", initial_sidebar_state="expanded")
db = load_db()

# --- SECURITY GATEKEEPER SYSTEM ---
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

# Sidebar Clean Styling
st.sidebar.markdown("### 🏆 Tournament Center")

# View Toggle
view_mode = st.sidebar.selectbox("Access Level", ["👥 Public View", "🛡️ Admin Console"])

# Handle Login Processing Securely
if view_mode == "🛡️ Admin Console" and not st.session_state.admin_authenticated:
    st.sidebar.markdown("---")
    admin_password = st.sidebar.text_input("Admin Password", type="password", key="admin_pwd_input")
    if st.sidebar.button("Verify Key"):
        # Put your unique custom password here
        if admin_password == "admin123": 
            st.session_state.admin_authenticated = True
            st.sidebar.success("Access Granted")
            st.rerun()
        else:
            st.sidebar.error("Invalid Admin Key")

# Determine Dynamic Menu Navigation Options Based on Visibility Rights
is_admin = view_mode == "🛡️ Admin Console" and st.session_state.admin_authenticated

if is_admin:
    menu = st.sidebar.radio("Control Panel", ["Leaderboard", "Prediction Grid", "Manage Games", "Participants", "Share & Export"])
else:
    menu = st.sidebar.radio("Dashboard Navigation", ["Leaderboard", "Prediction Grid"])
    if view_mode == "🛡️ Admin Console":
        st.info("Please complete authentication on the sidebar widget to reveal configuration workflows.")

st.sidebar.markdown("---")
if st.session_state.admin_authenticated:
    if st.sidebar.button("🚪 Close Admin Session"):
        st.session_state.admin_authenticated = False
        st.rerun()

# --- MENU TAB 1: LEADERBOARD ---
if menu == "Leaderboard":
    st.title("🏆 Leaderboard Rankings")
    
    leader_rows = []
    for p in db.get("participants", []):
        total_score = 0
        exact_count = 0
        outcome_count = 0
        wrong_count = 0
        completed_games = 0
        
        p_preds = [pr for pr in db.get("predictions", []) if pr["participantId"] == p["id"]]
        for pred in p_preds:
            fix = next((f for f in db.get("fixtures", []) if f["id"] == pred["fixtureId"]), None)
            
            if fix and fix.get("status") == "FINISHED" and fix.get("scoreA") is not None and fix.get("scoreB") is not None:
                if pred.get("scoreA") is not None and pred.get("scoreB") is not None:
                    completed_games += 1
                    pts = compute_points(pred["scoreA"], pred["scoreB"], fix["scoreA"], fix["scoreB"])
                    if pts == 4:
                        exact_count += 1
                        total_score += 4
                    elif pts == 3:
                        outcome_count += 1
                        total_score += 3
                    else:
                        wrong_count += 1
                    
        leader_rows.append({
            "Participant": p["name"],
            "Total Points": total_score,
            "Exact Scores (4pt)": exact_count,
            "Correct Outcomes (3pt)": outcome_count,
            "Incorrect (0pt)": wrong_count,
            "Matches Reviewed": completed_games
        })
        
    if leader_rows:
        df_leader = pd.DataFrame(leader_rows)
        # Sort primarily by total points, then by exact scores tiebreaker
        df_leader = df_leader.sort_values(by=["Total Points", "Exact Scores (4pt)", "Matches Reviewed"], ascending=[False, False, True]).reset_index(drop=True)
        df_leader.index = df_leader.index + 1
        df_leader.index.name = "Rank"
        
        st.dataframe(
            df_leader, 
            use_container_width=True,
            column_config={
                "Participant": st.column_config.TextColumn("Competitor Name"),
                "Total Points": st.column_config.NumberColumn("Total Score", format="%d")
            }
        )
    else:
        st.info("No competitors registered on the leaderboard database yet.")

    st.markdown("<br><hr>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.subheader("🟢 Finished Match Arena")
        finished_matches = [f for f in db.get("fixtures", []) if f["status"] == "FINISHED"]
        
        if not finished_matches:
            st.caption("No tournament matches have concluded yet.")
        else:
            for f in finished_matches:
                st.markdown(
                    f"<div style='background-color:rgba(40,167,69,0.1); padding:12px; border-radius:8px; margin-bottom:12px; border-left: 5px solid #28a745;'>"
                    f"<span style='font-size: 0.8em; text-transform: uppercase; letter-spacing: 1px; color: #888;'>{f['phase']}</span><br>"
                    f"<div style='font-size: 1.15em; font-weight: 700; margin-top:4px;'>"
                    f"{get_flag(f['teamA'])} {f['teamA']} <span style='color:#28a745;'>{f['scoreA']}</span> — <span style='color:#28a745;'>{f['scoreB']}</span> {f['teamB']} {get_flag(f['teamB'])}"
                    f"</div></div>", 
                    unsafe_allow_html=True
                )
                
    with col2:
        st.subheader("⏳ Scheduled Lineups")
        pending_matches = [f for f in db.get("fixtures", []) if f["status"] == "PENDING"]
        
        if not pending_matches:
            st.caption("No future fixtures found in the system queue.")
        else:
            for f in pending_matches:
                st.markdown(
                    f"<div style='background-color:rgba(0,0,0,0.05); padding:12px; border-radius:8px; margin-bottom:12px; border-left: 5px solid #6c757d;'>"
                    f"<span style='font-size: 0.8em; text-transform: uppercase; letter-spacing: 1px; color: #777;'>{f['phase']} &nbsp;|&nbsp; 🗓️ {f['date']} @ {format_time(f['time'])}</span><br>"
                    f"<div style='font-size: 1.1em; font-weight: 600; margin-top:4px; color:#ddd;'>"
                    f"{get_flag(f['teamA'])} {f['teamA']} <span style='color:#888; font-weight:300;'>vs</span> {f['teamB']} {get_flag(f['teamB'])}"
                    f"</div></div>", 
                    unsafe_allow_html=True
                )

# --- MENU TAB 2: PREDICTION GRID ---
elif menu == "Prediction Grid":
    st.title("📝 Competitor Profiles & Forecasts")
    participants = db.get("participants", [])
    fixtures = db.get("fixtures", [])
    
    if not participants:
        st.warning("No participants are enrolled. Database records are empty.")
    elif not fixtures:
        st.warning("No matches available. Create fixtures in the Match Editor tab.")
    else:
        part_dict = {p["id"]: p["name"] for p in participants}
        selected_id = st.selectbox("Select Competitor Profile:", list(part_dict.keys()), format_func=lambda x: part_dict[x])
        
        preds = db.get("predictions", [])
        saved_preds_dict = {(p["participantId"], p["fixtureId"]): p for p in preds}
        
        if is_admin:
            # ADMIN VIEW: Editable Grid
            updated_preds = []
            with st.form("prediction_submission_form", clear_on_submit=False):
                st.markdown(f"#### Logged Predictions Matrix for: **{part_dict[selected_id]}** (Admin Mode)")
                
                col_h1, col_h2, col_h3, col_h4 = st.columns([2.5, 3.5, 1, 1])
                col_h1.caption("ROUND CONTEXT")
                col_h2.caption("UPCOMING MATCHUP")
                col_h3.caption("HOME PREDICTION")
                col_h4.caption("AWAY PREDICTION")
                st.divider()

                for f in fixtures:
                    curr_pred = saved_preds_dict.get((selected_id, f["id"]), None)
                    default_val_A = int(curr_pred["scoreA"]) if (curr_pred is not None and curr_pred.get("scoreA") is not None) else None
                    default_val_B = int(curr_pred["scoreB"]) if (curr_pred is not None and curr_pred.get("scoreB") is not None) else None
                    
                    col_info, col_match, col_a, col_b = st.columns([2.5, 3.5, 1, 1])
                    with col_info:
                        st.markdown(f"**{f['phase']}**<br><span style='font-size:0.85em; color:gray;'>{f['date']} @ {format_time(f['time'])}</span>", unsafe_allow_html=True)
                    with col_match:
                        st.markdown(f"**{get_flag(f['teamA'])} {f['teamA']}** vs **{f['teamB']} {get_flag(f['teamB'])}**")
                    with col_a:
                        val_A = st.number_input("Home", min_value=0, max_value=20, value=default_val_A, placeholder="--", key=f"predA_{f['id']}_{selected_id}", label_visibility="collapsed")
                    with col_b:
                        val_B = st.number_input("Away", min_value=0, max_value=20, value=default_val_B, placeholder="--", key=f"predB_{f['id']}_{selected_id}", label_visibility="collapsed")
                    
                    st.markdown("<hr style='margin:8px 0; border-top:1px dashed rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
                    updated_preds.append({"participantId": selected_id, "fixtureId": f["id"], "scoreA": val_A, "scoreB": val_B})
                    
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("💾 Save Matrix Predictions", use_container_width=True):
                    other_preds = [p for p in preds if p["participantId"] != selected_id]
                    db["predictions"] = other_preds + updated_preds
                    save_db(db)
                    st.success(f"Predictions matrix updated successfully for {part_dict[selected_id]}!")
                    st.rerun()
        else:
            # PUBLIC VIEW: Read-Only Locked Mode
            st.markdown(f"#### Locked Score Card for: **{part_dict[selected_id]}**")
            
            col_h1, col_h2, col_h3 = st.columns([3, 4, 2])
            col_h1.caption("ROUND CONTEXT")
            col_h2.caption("MATCHUP")
            col_h3.caption("SUBMITTED FORECAST")
            st.divider()

            for f in fixtures:
                curr_pred = saved_preds_dict.get((selected_id, f["id"]), None)
                
                col_info, col_match, col_score = st.columns([3, 4, 2])
                with col_info:
                    st.markdown(f"**{f['phase']}**<br><span style='font-size:0.85em; color:gray;'>{f['date']}</span>", unsafe_allow_html=True)
                with col_match:
                    st.markdown(f"{get_flag(f['teamA'])} {f['teamA']} vs {f['teamB']} {get_flag(f['teamB'])}")
                with col_score:
                    if curr_pred is not None and curr_pred.get("scoreA") is not None and curr_pred.get("scoreB") is not None:
                        st.markdown(f"🎯 **{curr_pred['scoreA']} — {curr_pred['scoreB']}**")
                    else:
                        st.markdown("<span style='color:gray;'>No forecast logged</span>", unsafe_allow_html=True)
                
                st.markdown("<hr style='margin:6px 0; border-top:1px dashed rgba(255,255,255,0.05);'>", unsafe_allow_html=True)

# --- MENU TAB 3: MANAGE GAMES ---
elif menu == "Manage Games":
    st.title("⚙️ Tournament Match Controller")
    
    with st.expander("➕ Create New Match Fixture Entry", expanded=False):
        with st.form("add_new_fixture_form"):
            col_t1, col_t2 = st.columns(2)
            teamA = col_t1.selectbox("Home Team Designation", sorted(TEAMS))
            teamB = col_t2.selectbox("Away Team Designation", sorted(TEAMS))
            phase = st.text_input("Tournament Phase / Bracket Context", "Group Stage")
            
            st.markdown("**Kick-off Execution Clock**")
            col_d, col_h, col_m, col_p = st.columns([2, 1, 1, 1])
            date_val = col_d.date_input("Scheduled Date Mapping")
            hr_val = col_h.selectbox("Hour", ["12", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11"], index=3)
            min_val = col_m.selectbox("Minute", ["00", "15", "30", "45"])
            ampm_val = col_p.selectbox("Standard Window", ["AM", "PM"], index=1)
            
            if st.form_submit_button("Generate Match Configuration", use_container_width=True):
                if teamA == teamB:
                    st.error("Invalid Matching: Selection contains mirroring identical teams.")
                else:
                    h_int = int(hr_val)
                    if ampm_val == "PM" and h_int != 12: h_int += 12
                    elif ampm_val == "AM" and h_int == 12: h_int = 0
                    saved_time_str = f"{h_int:02d}:{min_val}"

                    new_fixture = {
                        "id": f"f_{int(datetime.now().timestamp())}",
                        "teamA": teamA,
                        "teamB": teamB,
                        "date": str(date_val),
                        "time": saved_time_str,
                        "phase": phase,
                        "scoreA": None,
                        "scoreB": None,
                        "status": "PENDING"
                    }
                    db["fixtures"].append(new_fixture)
                    save_db(db)
                    st.success(f"Match Established: {teamA} vs {teamB}")
                    st.rerun()

    st.subheader("Modify Matrix Fixtures & Official Scores")
    if not db.get("fixtures", []):
        st.info("No games scheduled on database layers yet.")
    else:
        col_h1, col_h2, col_h3, col_h4, col_h5, col_h6 = st.columns([2, 3.5, 1, 1, 1.5, 1.5])
        col_h1.caption("ROUND INFO")
        col_h2.caption("CONTESTANTS")
        col_h3.caption("HOME SCORE")
        col_h4.caption("AWAY SCORE")
        col_h5.caption("COMPLETION")
        col_h6.caption("COMMITMENT")
        st.divider()
        
        for f in db.get("fixtures", []):
            col_info, col_match, col_a, col_b, col_status, col_btn = st.columns([2, 3.5, 1, 1, 1.5, 1.5])
            
            with col_info:
                st.markdown(f"**{f['phase']}**<br><span style='font-size:0.85em; color:gray;'>{f['date']}</span>", unsafe_allow_html=True)
            with col_match:
                st.markdown(f"{get_flag(f['teamA'])} **{f['teamA']}**<br>{get_flag(f['teamB'])} **{f['teamB']}**", unsafe_allow_html=True)
            with col_a:
                val_sa = st.number_input("Score A", min_value=0, max_value=20, value=f["scoreA"] if f.get("scoreA") is not None else None, placeholder="-", key=f"admin_sa_{f['id']}", label_visibility="collapsed")
            with col_b:
                val_sb = st.number_input("Score B", min_value=0, max_value=20, value=f["scoreB"] if f.get("scoreB") is not None else None, placeholder="-", key=f"admin_sb_{f['id']}", label_visibility="collapsed")
            with col_status:
                status_val = st.selectbox("State Status", ["PENDING", "FINISHED"], index=0 if f["status"] == "PENDING" else 1, key=f"admin_st_{f['id']}", label_visibility="collapsed")
            with col_btn:
                if st.button("Update", key=f"admin_btn_{f['id']}", use_container_width=True):
                    f["scoreA"] = val_sa
                    f["scoreB"] = val_sb
                    f["status"] = status_val
                    save_db(db)
                    st.success("Matrix Synchronized")
                    st.rerun()
                    
            st.markdown("<hr style='margin:4px 0; rgba(255,255,255,0.05);'>", unsafe_allow_html=True)

# --- MENU TAB 4: PARTICIPANTS ---
elif menu == "Participants":
    st.title("👥 Registry Profile Manager")
    
    with st.form("enroll_player_form", clear_on_submit=True):
        new_player_name = st.text_input("Enter New Player Name:")
        if st.form_submit_button("Register Participant Profile", use_container_width=True):
            if new_player_name.strip() == "":
                st.error("Submission rejected: Identification name string cannot be blank.")
            else:
                new_id = f"p_{int(datetime.now().timestamp())}"
                db["participants"].append({"id": new_id, "name": new_player_name.strip()})
                save_db(db)
                st.success(f"Profile locked: Enrolled {new_player_name.strip()} successfully!")
                st.rerun()
                
    st.subheader("Current Registered Roster")
    st.divider()
    if not db.get("participants", []):
        st.info("Roster empty. No profiles built yet.")
    else:
        for p in db.get("participants", []):
            c_name, c_delete = st.columns([5, 1])
            with c_name:
                st.markdown(f"👤 **{p['name']}** &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:gray; font-size:0.85em;'>ID: `{p['id']}`</span>", unsafe_allow_html=True)
            with c_delete:
                if st.button("🗑️ Wipe Profile", key=f"del_{p['id']}", use_container_width=True):
                    db["participants"] = [x for x in db["participants"] if x["id"] != p["id"]]
                    db["predictions"] = [x for x in db["predictions"] if x["participantId"] != p["id"]]
                    save_db(db)
                    st.warning(f"Purged: Checked profile for {p['name']} removed entirely.")
                    st.rerun()
            st.markdown("<hr style='margin:4px 0; border-top:1px dashed rgba(255,255,255,0.05);'>", unsafe_allow_html=True)

# --- MENU TAB 5: SHARE & EXPORT ---
elif menu == "Share & Export":
    st.title("📸 Report Exportation Desk")
    st.markdown("Extract centralized auditing metrics to compile offline or review comprehensive individual player prediction spreadsheets.")
    
    participants = db.get("participants", [])
    fixtures = db.get("fixtures", [])
    predictions = db.get("predictions", [])
    
    if not participants or not fixtures:
        st.info("System tracking reports require an active lineup configuration along with standard enrolled competitor metrics.")
    else:
        unified_data = []
        
        for p in participants:
            total_score = 0
            exact_count = 0
            outcome_count = 0
            
            row_data = {"Participant": p["name"]}
            match_breakdowns = {}
            p_preds = [pr for pr in predictions if pr["participantId"] == p["id"]]
            
            for f in fixtures:
                is_finished = f.get("status") == "FINISHED" and f.get("scoreA") is not None and f.get("scoreB") is not None
                
                if is_finished:
                    match_header = f"{f['teamA']} vs {f['teamB']} [{f['scoreA']}-{f['scoreB']}]"
                else:
                    match_header = f"{f['teamA']} vs {f['teamB']} [Pending]"
                
                pred = next((pr for pr in p_preds if pr["fixtureId"] == f["id"]), None)
                
                if pred is not None and pred.get("scoreA") is not None and pred.get("scoreB") is not None:
                    pred_str = f"{pred['scoreA']}-{pred['scoreB']}"
                    
                    if is_finished:
                        pts = compute_points(pred["scoreA"], pred["scoreB"], f["scoreA"], f["scoreB"])
                        if pts == 4: exact_count += 1
                        if pts == 3: outcome_count += 1
                        total_score += pts
                        
                        match_breakdowns[match_header] = f"{pred_str} ({pts} pts)"
                    else:
                        match_breakdowns[match_header] = pred_str
                else:
                    match_breakdowns[match_header] = "Unselected (0 pts)" if is_finished else "Unselected"
            
            row_data["Total Points"] = total_score
            row_data["Exact Scores (4pt)"] = exact_count
            row_data["Correct Outcomes (3pt)"] = outcome_count
            
            row_data.update(match_breakdowns)
            unified_data.append(row_data)
            
        df_unified = pd.DataFrame(unified_data)
        df_unified = df_unified.sort_values(by=["Total Points", "Exact Scores (4pt)"], ascending=[False, False])
        
        st.subheader("📋 Comprehensive Performance Matrix")
        st.dataframe(df_unified, use_container_width=True)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_unified.to_excel(writer, sheet_name='Audit Report Sheet', index=False)
            
        st.markdown("<br>", unsafe_allow_html=True)
        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            st.download_button(
                label="📥 Download Master Audit Spreadsheet (.xlsx)",
                data=output.getvalue(),
                file_name="Tournament_Core_Audit_Log.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with col_ex2:
            json_string = json.dumps(db, indent=4)
            st.download_button(
                label="📥 Download Complete Database Backup (.json)",
                data=json_string,
                file_name="system_data_backup.json",
                mime="application/json",
                use_container_width=True
            )