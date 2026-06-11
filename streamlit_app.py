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

# --- POINT COMPUTATION ---
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
st.set_page_config(page_title="WC2026 Dashboard", layout="wide", initial_sidebar_state="collapsed") # Collapsed by default for mobile
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
    st.title("🏆 Leaderboard")
    
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
            "Pts": total_score,
            "Exact (4)": exact_count,
            "Outcome (3)": outcome_count,
            "Missed (0)": wrong_count,
            "Played": completed_games
        })
        
    if leader_rows:
        df_leader = pd.DataFrame(leader_rows)
        # Sort primarily by total points, then by exact scores tiebreaker
        df_leader = df_leader.sort_values(by=["Pts", "Exact (4)", "Played"], ascending=[False, False, True]).reset_index(drop=True)
        df_leader.index = df_leader.index + 1
        df_leader.index.name = "Rank"
        
        st.dataframe(
            df_leader, 
            use_container_width=True,
            column_config={
                "Participant": st.column_config.TextColumn("Competitor"),
                "Pts": st.column_config.NumberColumn("Total Pts", format="%d")
            }
        )
    else:
        st.info("No competitors registered on the leaderboard yet.")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Mobile-friendly display: removed columns, using stacked approach
    st.subheader("🟢 Finished Matches")
    finished_matches = [f for f in db.get("fixtures", []) if f["status"] == "FINISHED"]
    
    if not finished_matches:
        st.caption("No matches have concluded yet.")
    else:
        for f in finished_matches:
            with st.container(border=True):
                st.caption(f"{f['phase']}")
                st.markdown(f"#### {get_flag(f['teamA'])} {f['teamA']} <span style='color:#28a745;'>{f['scoreA']}</span> — <span style='color:#28a745;'>{f['scoreB']}</span> {f['teamB']} {get_flag(f['teamB'])}", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.subheader("⏳ Upcoming Matches")
    pending_matches = [f for f in db.get("fixtures", []) if f["status"] == "PENDING"]
    
    if not pending_matches:
        st.caption("No upcoming matches scheduled.")
    else:
        for f in pending_matches:
            with st.container(border=True):
                st.caption(f"{f['phase']} | 🗓️ {f['date']} @ {format_time(f['time'])}")
                st.markdown(f"**{get_flag(f['teamA'])} {f['teamA']}** vs **{f['teamB']} {get_flag(f['teamB'])}**", unsafe_allow_html=True)

# --- MENU TAB 2: PREDICTION GRID ---
elif menu == "Prediction Grid":
    st.title("📝 Forecasts")
    participants = db.get("participants", [])
    fixtures = db.get("fixtures", [])
    
    if not participants:
        st.warning("No participants enrolled.")
    elif not fixtures:
        st.warning("No matches available.")
    else:
        part_dict = {p["id"]: p["name"] for p in participants}
        selected_id = st.selectbox("Competitor Profile:", list(part_dict.keys()), format_func=lambda x: part_dict[x])
        st.divider()
        
        preds = db.get("predictions", [])
        saved_preds_dict = {(p["participantId"], p["fixtureId"]): p for p in preds}
        
        if is_admin:
            # ADMIN VIEW: Editable Grid (Mobile Cards)
            updated_preds = []
            with st.form("prediction_submission_form", clear_on_submit=False):
                st.markdown(f"### Matrix for: **{part_dict[selected_id]}**")
                
                for f in fixtures:
                    curr_pred = saved_preds_dict.get((selected_id, f["id"]), None)
                    default_val_A = int(curr_pred["scoreA"]) if (curr_pred is not None and curr_pred.get("scoreA") is not None) else None
                    default_val_B = int(curr_pred["scoreB"]) if (curr_pred is not None and curr_pred.get("scoreB") is not None) else None
                    
                    with st.container(border=True):
                        st.caption(f"🗓️ {f['phase']} | {f['date']} @ {format_time(f['time'])}")
                        st.markdown(f"#### {get_flag(f['teamA'])} {f['teamA']} 🆚 {f['teamB']} {get_flag(f['teamB'])}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            val_A = st.number_input(f"{f['teamA']}", min_value=0, max_value=20, value=default_val_A, placeholder="--", key=f"predA_{f['id']}_{selected_id}")
                        with col2:
                            val_B = st.number_input(f"{f['teamB']}", min_value=0, max_value=20, value=default_val_B, placeholder="--", key=f"predB_{f['id']}_{selected_id}")
                            
                    updated_preds.append({"participantId": selected_id, "fixtureId": f["id"], "scoreA": val_A, "scoreB": val_B})
                    
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("💾 Save Matrix Predictions", use_container_width=True):
                    other_preds = [p for p in preds if p["participantId"] != selected_id]
                    db["predictions"] = other_preds + updated_preds
                    save_db(db)
                    st.success(f"Updated successfully for {part_dict[selected_id]}!")
                    st.rerun()
        else:
            # PUBLIC VIEW: Read-Only Locked Mode (Mobile Cards)
            st.markdown(f"### Score Card: **{part_dict[selected_id]}**")
            
            for f in fixtures:
                curr_pred = saved_preds_dict.get((selected_id, f["id"]), None)
                
                with st.container(border=True):
                    st.caption(f"{f['phase']} | {f['date']}")
                    st.markdown(f"**{get_flag(f['teamA'])} {f['teamA']}** vs **{f['teamB']} {get_flag(f['teamB'])}**")
                    
                    if curr_pred is not None and curr_pred.get("scoreA") is not None and curr_pred.get("scoreB") is not None:
                        st.success(f"🎯 Forecast Logged: **{curr_pred['scoreA']} — {curr_pred['scoreB']}**")
                    else:
                        st.info("No forecast logged")

# --- MENU TAB 3: MANAGE GAMES ---
elif menu == "Manage Games":
    st.title("⚙️ Match Controller")
    
    with st.expander("➕ Create New Match", expanded=False):
        with st.form("add_new_fixture_form"):
            teamA = st.selectbox("Home Team", sorted(TEAMS))
            teamB = st.selectbox("Away Team", sorted(TEAMS))
            phase = st.text_input("Tournament Phase", "Group Stage")
            
            st.markdown("**Kick-off Time**")
            date_val = st.date_input("Scheduled Date")
            
            col_h, col_m, col_p = st.columns([1, 1, 1])
            hr_val = col_h.selectbox("Hour", ["12", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11"], index=3)
            min_val = col_m.selectbox("Minute", ["00", "15", "30", "45"])
            ampm_val = col_p.selectbox("AM/PM", ["AM", "PM"], index=1)
            
            if st.form_submit_button("Generate Match", use_container_width=True):
                if teamA == teamB:
                    st.error("Invalid Matching: Teams must be different.")
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
                    st.success("Match Established!")
                    st.rerun()

    st.subheader("Official Scores & Matrix")
    if not db.get("fixtures", []):
        st.info("No games scheduled yet.")
    else:
        for f in db.get("fixtures", []):
            with st.container(border=True):
                st.caption(f"{f['phase']} | {f['date']}")
                st.markdown(f"**{get_flag(f['teamA'])} {f['teamA']}** vs **{f['teamB']} {get_flag(f['teamB'])}**")
                
                c_sa, c_sb = st.columns(2)
                with c_sa: 
                    val_sa = st.number_input(f"{f['teamA']} Score", min_value=0, max_value=20, value=f["scoreA"] if f.get("scoreA") is not None else None, placeholder="-", key=f"admin_sa_{f['id']}")
                with c_sb: 
                    val_sb = st.number_input(f"{f['teamB']} Score", min_value=0, max_value=20, value=f["scoreB"] if f.get("scoreB") is not None else None, placeholder="-", key=f"admin_sb_{f['id']}")
                
                st.divider()
                c_st, c_btn = st.columns(2)
                with c_st: 
                    status_val = st.selectbox("Match Status", ["PENDING", "FINISHED"], index=0 if f["status"] == "PENDING" else 1, key=f"admin_st_{f['id']}")
                with c_btn:
                    st.write("") # Spacer to align button with dropdown
                    st.write("") 
                    if st.button("💾 Update", key=f"admin_btn_{f['id']}", use_container_width=True):
                        f["scoreA"] = val_sa
                        f["scoreB"] = val_sb
                        f["status"] = status_val
                        save_db(db)
                        st.success("Synchronized!")
                        st.rerun()

# --- MENU TAB 4: PARTICIPANTS ---
elif menu == "Participants":
    st.title("👥 Registry")
    
    with st.form("enroll_player_form", clear_on_submit=True):
        new_player_name = st.text_input("Enter New Player Name:")
        if st.form_submit_button("Register Participant", use_container_width=True):
            if new_player_name.strip() == "":
                st.error("Name cannot be blank.")
            else:
                new_id = f"p_{int(datetime.now().timestamp())}"
                db["participants"].append({"id": new_id, "name": new_player_name.strip()})
                save_db(db)
                st.success(f"Enrolled {new_player_name.strip()}!")
                st.rerun()
                
    st.subheader("Current Roster")
    st.divider()
    if not db.get("participants", []):
        st.info("Roster empty.")
    else:
        for p in db.get("participants", []):
            with st.container(border=True):
                c_name, c_delete = st.columns([3, 1])
                with c_name:
                    st.markdown(f"**{p['name']}**")
                    st.caption(f"ID: `{p['id']}`")
                with c_delete:
                    if st.button("🗑️ Del", key=f"del_{p['id']}", use_container_width=True):
                        db["participants"] = [x for x in db["participants"] if x["id"] != p["id"]]
                        db["predictions"] = [x for x in db["predictions"] if x["participantId"] != p["id"]]
                        save_db(db)
                        st.rerun()

# --- MENU TAB 5: SHARE & EXPORT ---
elif menu == "Share & Export":
    st.title("📸 Report Export")
    st.markdown("Extract metrics for offline review.")
    
    participants = db.get("participants", [])
    fixtures = db.get("fixtures", [])
    predictions = db.get("predictions", [])
    
    if not participants or not fixtures:
        st.info("Reports require active participants and matches.")
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
        
        st.subheader("📋 Performance Matrix")
        st.dataframe(df_unified, use_container_width=True)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_unified.to_excel(writer, sheet_name='Audit Report', index=False)
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Stacked buttons for mobile
        st.download_button(
            label="📥 Download Excel (.xlsx)",
            data=output.getvalue(),
            file_name="Tournament_Audit_Log.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        json_string = json.dumps(db, indent=4)
        st.download_button(
            label="📥 Download Backup (.json)",
            data=json_string,
            file_name="system_data_backup.json",
            mime="application/json",
            use_container_width=True
        )