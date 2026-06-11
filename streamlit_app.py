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

# Force strictly 12-hour AM/PM format
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
    # If ANY score is missing (empty), return 0
    if act_A is None or act_B is None or pred_A is None or pred_B is None:
        return 0
    if int(pred_A) == int(act_A) and int(pred_B) == int(act_B):
        return 3
    act_outcome = 1 if act_A > act_B else (2 if act_A < act_B else 0)
    pred_outcome = 1 if pred_A > pred_B else (2 if pred_A < pred_B else 0)
    if act_outcome == pred_outcome:
        return 2
    return 0

db = load_db()

# --- APP LAYOUT ---
st.set_page_config(page_title="WC2026 Prediction System", layout="wide")
st.sidebar.title("🏆 WC2026 Tournament")
menu = st.sidebar.radio("Navigation Menu", ["Leaderboard", "Prediction Grid", "Manage Games", "Participants", "Share & Export"])

# --- MENU TAB 1: LEADERBOARD ---
if menu == "Leaderboard":
    st.title("🏆 Standings Leaderboard")
    st.markdown("Scoring: **3 points** for exact score, **2 points** for correct match outcome (Win/Loss/Draw), **0 points** otherwise.")
    
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
                    if pts == 3:
                        exact_count += 1
                        total_score += 3
                    elif pts == 2:
                        outcome_count += 1
                        total_score += 2
                    else:
                        wrong_count += 1
                    
        leader_rows.append({
            "Participant": p["name"],
            "Total Points": total_score,
            "Exact Scores (3pt)": exact_count,
            "Correct Outcomes (2pt)": outcome_count,
            "Incorrect (0pt)": wrong_count,
            "Games Checked": completed_games
        })
        
    if leader_rows:
        df_leader = pd.DataFrame(leader_rows)
        df_leader = df_leader.sort_values(by=["Total Points", "Exact Scores (3pt)", "Games Checked"], ascending=[False, False, True]).reset_index(drop=True)
        df_leader.index = df_leader.index + 1
        df_leader.index.name = "Rank"
        
       # Add visual emphasis to the table
        st.dataframe(
            df_leader, 
            use_container_width=True,
            column_config={
                "Participant": st.column_config.TextColumn("Participant"),
                "Total Points": st.column_config.NumberColumn("Total Points", format="%d")
            }
        )
    else:
        st.info("No participants registered yet.")

    st.markdown("---")
    st.subheader("📋 Match Schedule & Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🟢 Finished Matches")
        finished_matches = [f for f in db.get("fixtures", []) if f["status"] == "FINISHED"]
        
        if not finished_matches:
            st.caption("No matches finished yet.")
        else:
            for f in finished_matches:
                st.markdown(
                    f"<div style='margin-bottom: 10px;'>"
                    f"<span style='font-size: 0.85em; color: #888;'>{f['phase']}</span><br>"
                    f"<b>{get_flag(f['teamA'])} {f['teamA']} {f['scoreA']} - {f['scoreB']} {f['teamB']} {get_flag(f['teamB'])}</b>"
                    f"</div>", 
                    unsafe_allow_html=True
                )
                
    with col2:
        st.markdown("#### ⏳ Pending Matches")
        pending_matches = [f for f in db.get("fixtures", []) if f["status"] == "PENDING"]
        
        if not pending_matches:
            st.caption("No pending matches.")
        else:
            for f in pending_matches:
                st.markdown(
                    f"<div style='margin-bottom: 10px;'>"
                    f"<span style='font-size: 0.85em; color: #888;'>{f['phase']} &nbsp;|&nbsp; {f['date']} @ {format_time(f['time'])}</span><br>"
                    f"<b>{get_flag(f['teamA'])} {f['teamA']} vs {f['teamB']} {get_flag(f['teamB'])}</b>"
                    f"</div>", 
                    unsafe_allow_html=True
                )

# --- MENU TAB 2: PREDICTION GRID ---
elif menu == "Prediction Grid":
    st.title("📝 Enter Participant Predictions")
    participants = db.get("participants", [])
    fixtures = db.get("fixtures", [])
    
    if not participants:
        st.warning("Please add participants first via the 'Participants' tab.")
    elif not fixtures:
        st.warning("No matches have been created yet by the administrator.")
    else:
        part_dict = {p["id"]: p["name"] for p in participants}
        selected_id = st.selectbox("Select Competitor:", list(part_dict.keys()), format_func=lambda x: part_dict[x])
        
        preds = db.get("predictions", [])
        saved_preds_dict = {(p["participantId"], p["fixtureId"]): p for p in preds}
        
        updated_preds = []
        
        with st.form("prediction_submission_form"):
            st.markdown(f"#### Forecasts for: **{part_dict[selected_id]}**")
            
            # UI Header Row
            col_h1, col_h2, col_h3, col_h4 = st.columns([2.5, 3.5, 1, 1])
            col_h1.caption("MATCH INFO")
            col_h2.caption("FIXTURE")
            col_h3.caption("HOME SCORE")
            col_h4.caption("AWAY SCORE")
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
                
                st.markdown("---")
                updated_preds.append({"participantId": selected_id, "fixtureId": f["id"], "scoreA": val_A, "scoreB": val_B})
                
            if st.form_submit_button("💾 Save All Predictions for Player", use_container_width=True):
                other_preds = [p for p in preds if p["participantId"] != selected_id]
                db["predictions"] = other_preds + updated_preds
                save_db(db)
                st.success(f"Successfully recorded picks for {part_dict[selected_id]}!")
                st.rerun()

# --- MENU TAB 3: MANAGE GAMES ---
elif menu == "Manage Games":
    st.title("⚙️ Admin Match & Results Editor")
    
    with st.expander("➕ Add New Match Fixture", expanded=False):
        with st.form("add_new_fixture_form"):
            col_t1, col_t2 = st.columns(2)
            teamA = col_t1.selectbox("Home Country", sorted(TEAMS))
            teamB = col_t2.selectbox("Away Country", sorted(TEAMS))
            phase = st.text_input("Tournament Phase / Bracket Group", "Group Stage")
            
            st.markdown("**Kick-off Time**")
            col_d, col_h, col_m, col_p = st.columns([2, 1, 1, 1])
            date_val = col_d.date_input("Match Date")
            hr_val = col_h.selectbox("Hour", ["12", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11"], index=3)
            min_val = col_m.selectbox("Min", ["00", "15", "30", "45"])
            ampm_val = col_p.selectbox("AM/PM", ["AM", "PM"], index=1)
            
            if st.form_submit_button("Create Official Match"):
                if teamA == teamB:
                    st.error("A country cannot play against itself.")
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
                    st.success(f"Scheduled: {teamA} vs {teamB}")
                    st.rerun()

    st.subheader("Modify Existing Fixtures and Results")
    if not db.get("fixtures", []):
        st.info("No fixtures created yet.")
        
    # UI Header Row
    col_h1, col_h2, col_h3, col_h4, col_h5, col_h6 = st.columns([2, 3.5, 1, 1, 1.5, 1.5])
    col_h1.caption("MATCH INFO")
    col_h2.caption("FIXTURE")
    col_h3.caption("HOME")
    col_h4.caption("AWAY")
    col_h5.caption("STATUS")
    col_h6.caption("ACTION")
    st.divider()
    
    for f in db.get("fixtures", []):
        col_info, col_match, col_a, col_b, col_status, col_btn = st.columns([2, 3.5, 1, 1, 1.5, 1.5])
        
        with col_info:
            st.markdown(f"**{f['phase']}**<br><span style='font-size:0.85em; color:gray;'>{f['date']}</span>", unsafe_allow_html=True)
        with col_match:
            st.markdown(f"{get_flag(f['teamA'])} **{f['teamA']}**<br>{get_flag(f['teamB'])} **{f['teamB']}**", unsafe_allow_html=True)
        with col_a:
            val_sa = st.number_input("Home Score", min_value=0, max_value=20, value=f["scoreA"] if f.get("scoreA") is not None else None, placeholder="-", key=f"admin_sa_{f['id']}", label_visibility="collapsed")
        with col_b:
            val_sb = st.number_input("Away Score", min_value=0, max_value=20, value=f["scoreB"] if f.get("scoreB") is not None else None, placeholder="-", key=f"admin_sb_{f['id']}", label_visibility="collapsed")
        with col_status:
            status_val = st.selectbox("State", ["PENDING", "FINISHED"], index=0 if f["status"] == "PENDING" else 1, key=f"admin_st_{f['id']}", label_visibility="collapsed")
        with col_btn:
            if st.button("Save", key=f"admin_btn_{f['id']}", use_container_width=True):
                f["scoreA"] = val_sa
                f["scoreB"] = val_sb
                f["status"] = status_val
                save_db(db)
                st.success("Updated!")
                st.rerun()
                
        st.markdown("---")
# --- MENU TAB 4: PARTICIPANTS ---
elif menu == "Participants":
    st.title("👥 Enroll Competitors")
    
    with st.form("enroll_player_form"):
        new_player_name = st.text_input("Enter New Player Name:")
        if st.form_submit_button("Register Participant"):
            if new_player_name.strip() == "":
                st.error("Name cannot be blank.")
            else:
                new_id = f"p_{int(datetime.now().timestamp())}"
                db["participants"].append({"id": new_id, "name": new_player_name.strip()})
                save_db(db)
                st.success(f"Enrolled {new_player_name.strip()} successfully!")
                st.rerun()
                
    st.subheader("Current Registered Competitors")
    if not db.get("participants", []):
        st.info("No players enrolled yet.")
    for p in db.get("participants", []):
        st.markdown(f"👤 **{p['name']}** (ID: `{p['id']}`)")

# --- MENU TAB 5: SHARE & EXPORT ---
elif menu == "Share & Export":
    st.title("📸 Share Predictions & Export Data")
    st.markdown("Download the unified Master Audit Sheet. This single Excel sheet contains the leaderboard totals and a complete breakdown of exactly how many points each player earned for every match.")
    
    participants = db.get("participants", [])
    fixtures = db.get("fixtures", [])
    predictions = db.get("predictions", [])
    
    if not participants or not fixtures:
        st.info("You need to add participants and fixtures before you can generate a shareable grid or report.")
    else:
        # --- PREPARE UNIFIED AUDIT MATRIX DATA ---
        unified_data = []
        
        for p in participants:
            total_score = 0
            exact_count = 0
            outcome_count = 0
            
            # Start building the row with basic info
            row_data = {"Participant": p["name"]}
            match_breakdowns = {}
            
            # Fetch all predictions for this user
            p_preds = [pr for pr in predictions if pr["participantId"] == p["id"]]
            
            for f in fixtures:
                # Determine if match is finished to show points
                is_finished = f.get("status") == "FINISHED" and f.get("scoreA") is not None and f.get("scoreB") is not None
                
                # Create the Column Header (showing the real outcome if finished)
                if is_finished:
                    match_header = f"{f['teamA']} vs {f['teamB']} [Result: {f['scoreA']}-{f['scoreB']}]"
                else:
                    match_header = f"{f['teamA']} vs {f['teamB']} [Pending]"
                
                # Find the specific prediction
                pred = next((pr for pr in p_preds if pr["fixtureId"] == f["id"]), None)
                
                if pred is not None and pred.get("scoreA") is not None and pred.get("scoreB") is not None:
                    pred_str = f"{pred['scoreA']}-{pred['scoreB']}"
                    
                    if is_finished:
                        pts = compute_points(pred["scoreA"], pred["scoreB"], f["scoreA"], f["scoreB"])
                        if pts == 3: exact_count += 1
                        if pts == 2: outcome_count += 1
                        total_score += pts
                        
                        match_breakdowns[match_header] = f"{pred_str} ({pts} pts)"
                    else:
                        match_breakdowns[match_header] = pred_str
                else:
                    # They didn't make a pick or it was left entirely blank
                    match_breakdowns[match_header] = "No Pick (0 pts)" if is_finished else "No Pick"
            
            # Add the totals to the row
            row_data["Total Points"] = total_score
            row_data["Exact Scores (3pt)"] = exact_count
            row_data["Correct Outcomes (2pt)"] = outcome_count
            
            # Merge the match breakdowns into the row
            row_data.update(match_breakdowns)
            unified_data.append(row_data)
            
        # Convert to DataFrame and sort by Top Score
        df_unified = pd.DataFrame(unified_data)
        df_unified = df_unified.sort_values(by=["Total Points", "Exact Scores (3pt)"], ascending=[False, False])
        
        st.subheader("📋 Master Audit Matrix Preview")
        st.dataframe(df_unified, use_container_width=True)
        
        # --- EXCEL EXPORT (Single Sheet) ---
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_unified.to_excel(writer, sheet_name='Audit Sheet', index=False)
            
        st.download_button(
            label="📥 Download Master Audit Sheet (Excel)",
            data=output.getvalue(),
            file_name="Tournament_Audit_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    st.markdown("---")
    st.subheader("💾 System Database Backup")
    json_string = json.dumps(db, indent=4)
    st.download_button(
        label="📥 Download System Backup (data.json)",
        data=json_string,
        file_name="data_backup.json",
        mime="application/json"
    )