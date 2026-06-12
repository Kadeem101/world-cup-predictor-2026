import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
from io import BytesIO

# Database Path
DB_FILE = "data.json"

# --- CONFIGURATION ---
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
    "Argentina": "![AR](https://flagcdn.com/16x12/ar.png)", 
    "Australia": "![AU](https://flagcdn.com/16x12/au.png)", 
    "Austria": "![AT](https://flagcdn.com/16x12/at.png)", 
    "Belgium": "![BE](https://flagcdn.com/16x12/be.png)",
    "Bosnia and Herzegovina": "![BA](https://flagcdn.com/16x12/ba.png)", 
    "Brazil": "![BR](https://flagcdn.com/16x12/br.png)", 
    "Canada": "![CA](https://flagcdn.com/16x12/ca.png)", 
    "Cape Verde": "![CV](https://flagcdn.com/16x12/cv.png)",
    "Colombia": "![CO](https://flagcdn.com/16x12/co.png)", 
    "Croatia": "![HR](https://flagcdn.com/16x12/hr.png)", 
    "Curaçao": "![CW](https://flagcdn.com/16x12/cw.png)", 
    "Czechia": "![CZ](https://flagcdn.com/16x12/cz.png)",
    "DR Congo": "![CD](https://flagcdn.com/16x12/cd.png)", 
    "Ecuador": "![EC](https://flagcdn.com/16x12/ec.png)", 
    "Egypt": "![EG](https://flagcdn.com/16x12/eg.png)", 
    "England": "![GB-ENG](https://flagcdn.com/16x12/gb-eng.png)",
    "France": "![FR](https://flagcdn.com/16x12/fr.png)", 
    "Germany": "![DE](https://flagcdn.com/16x12/de.png)", 
    "Ghana": "![GH](https://flagcdn.com/16x12/gh.png)", 
    "Haiti": "![HT](https://flagcdn.com/16x12/ht.png)",
    "Iran": "![IR](https://flagcdn.com/16x12/ir.png)", 
    "Iraq": "![IQ](https://flagcdn.com/16x12/iq.png)", 
    "Ivory Coast": "![CI](https://flagcdn.com/16x12/ci.png)", 
    "Japan": "![JP](https://flagcdn.com/16x12/jp.png)",
    "Jordan": "![JO](https://flagcdn.com/16x12/jo.png)", 
    "Mexico": "![MX](https://flagcdn.com/16x12/mx.png)", 
    "Morocco": "![MA](https://flagcdn.com/16x12/ma.png)", 
    "Netherlands": "![NL](https://flagcdn.com/16x12/nl.png)",
    "New Zealand": "![NZ](https://flagcdn.com/16x12/nz.png)", 
    "Norway": "![NO](https://flagcdn.com/16x12/no.png)", 
    "Panama": "![PA](https://flagcdn.com/16x12/pa.png)", 
    "Paraguay": "![PY](https://flagcdn.com/16x12/py.png)",
    "Portugal": "![PT](https://flagcdn.com/16x12/pt.png)", 
    "Qatar": "![QA](https://flagcdn.com/16x12/qa.png)", 
    "Saudi Arabia": "![SA](https://flagcdn.com/16x12/sa.png)", 
    "Scotland": "![GB-SCT](https://flagcdn.com/16x12/gb-sct.png)",
    "Senegal": "![SN](https://flagcdn.com/16x12/sn.png)", 
    "South Africa": "![ZA](https://flagcdn.com/16x12/za.png)", 
    "South Korea": "![KR](https://flagcdn.com/16x12/kr.png)", 
    "Spain": "![ES](https://flagcdn.com/16x12/es.png)",
    "Sweden": "![SE](https://flagcdn.com/16x12/se.png)", 
    "Switzerland": "![CH](https://flagcdn.com/16x12/ch.png)", 
    "Tunisia": "![TN](https://flagcdn.com/16x12/tn.png)", 
    "Turkey": "![TR](https://flagcdn.com/16x12/tr.png)",
    "USA": "![US](https://flagcdn.com/16x12/us.png)", 
    "Uruguay": "![UY](https://flagcdn.com/16x12/uy.png)", 
    "Uzbekistan": "![UZ](https://flagcdn.com/16x12/uz.png)"
}

def get_flag(team): return FLAGS.get(team, "⚽")

def format_date(date_str):
    try: return datetime.strptime(date_str, "%Y-%m-%d").strftime("%a. %d %B")
    except: return date_str

def format_time(time_str):
    if not time_str: return "TBD"
    try: return datetime.strptime(time_str[:5], "%H:%M").strftime("%I:%M %p")
    except: return time_str

def load_db():
    if not os.path.exists(DB_FILE): return {"participants": [], "fixtures": [], "predictions": [], "teams": TEAMS}
    with open(DB_FILE, "r") as f: return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

def compute_points(pred_A, pred_B, act_A, act_B):
    if act_A is None or act_B is None or pred_A is None or pred_B is None: return 0
    pA, pB, aA, aB = int(pred_A), int(pred_B), int(act_A), int(act_B)
    act_outcome = 1 if aA > aB else (2 if aA < aB else 0)
    pred_outcome = 1 if pA > pB else (2 if pA < pB else 0)
    if act_outcome == pred_outcome: return 4 if pA == aA and pB == aB else 3
    return 0

# --- START UP ---
st.set_page_config(page_title="WC2026 Dashboard", layout="wide", initial_sidebar_state="collapsed")
db = load_db()
if "admin_authenticated" not in st.session_state: st.session_state.admin_authenticated = False

# --- NAVIGATION ---
view_mode = st.sidebar.selectbox("Access Level", ["👥 Public View", "🛡️ Admin Console"])
is_admin = view_mode == "🛡️ Admin Console" and st.session_state.admin_authenticated

if view_mode == "🛡️ Admin Console" and not st.session_state.admin_authenticated:
    key = st.sidebar.text_input("Admin Key", type="password")
    if st.sidebar.button("Verify Key"):
        if key == "admin123":
            st.session_state.admin_authenticated = True
            st.sidebar.success("Access Granted")
            st.rerun()
        else:
            st.sidebar.error("Invalid Key")

if st.session_state.admin_authenticated:
    if st.sidebar.button("🚪 Close Session"):
        st.session_state.admin_authenticated = False
        st.rerun()

# -------------------------------------------------------------
# UPDATED MENU LOGIC: Leaderboard is the only public page.
# -------------------------------------------------------------
options = ["Leaderboard"]
if is_admin:
    options += ["Enter/Update Scores", "Manage Games", "Participants", "Share & Export"]

menu = st.sidebar.radio("Menu", options)

# --- TAB: LEADERBOARD ---
if menu == "Leaderboard":
    st.title("🏆 Leaderboard")
    
    tab_standings, tab_matrix = st.tabs(["📊 Standings & Fixtures", "👀 Extended View"])
    
    with tab_standings:
        leader_rows = []
        for p in db.get("participants", []):
            total, exact, outcome, completed = 0, 0, 0, 0
            p_preds = [pr for pr in db.get("predictions", []) if pr["participantId"] == p["id"]]
            for pred in p_preds:
                fix = next((f for f in db.get("fixtures", []) if f["id"] == pred["fixtureId"]), None)
                if fix and fix.get("status") == "FINISHED":
                    completed += 1
                    pts = compute_points(pred.get("scoreA"), pred.get("scoreB"), fix.get("scoreA"), fix.get("scoreB"))
                    if pts == 4: exact += 1
                    if pts >= 3: outcome += 1
                    total += pts
            leader_rows.append({"Participant": p["name"], "Total Pts": total, "Exact (4)": exact, "Won / Draw (3)": outcome})
        
        if leader_rows:
            df = pd.DataFrame(leader_rows).sort_values(by="Total Pts", ascending=False).reset_index(drop=True)
            df.index += 1
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No participants registered on the leaderboard yet.")

        st.subheader("🟢 Finished Matches")
        finished_matches = [f for f in db.get("fixtures", []) if f["status"] == "FINISHED"]
        if finished_matches:
            with st.expander("Show/Hide Completed Matches"):
                for f in finished_matches:
                    st.markdown(f"{get_flag(f['teamA'])} {f['teamA']} **{f['scoreA']}-{f['scoreB']}** {f['teamB']} {get_flag(f['teamB'])}")
        else:
            st.caption("No matches have concluded yet.")

        st.subheader("⏳ Upcoming Matches")
        pending_matches = [f for f in db.get("fixtures", []) if f["status"] == "PENDING"]
        if pending_matches:
            for f in pending_matches:
                with st.container(border=True):
                    st.caption(f"{format_date(f['date'])} | {format_time(f['time'])}")
                    st.markdown(f"{get_flag(f['teamA'])} {f['teamA']} vs {f['teamB']} {get_flag(f['teamB'])}")
        else:
            st.caption("No upcoming matches scheduled.")

    with tab_matrix:
        participants = db.get("participants", [])
        fixtures = db.get("fixtures", [])
        predictions = db.get("predictions", [])
        
        if not participants or not fixtures:
            st.info("The performance matrix will populate once matches and participants are configured.")
        else:
            unified_data = []
            match_headers_list = []
            
            for f in fixtures:
                is_finished = f.get("status") == "FINISHED" and f.get("scoreA") is not None and f.get("scoreB") is not None
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
                        else:
                            match_breakdowns[match_header] = pred_str
                    else:
                        match_breakdowns[match_header] = "Unselected"
                
                row_data["Total Points"] = total_score
                row_data["Exact (4pt)"] = exact_count
                row_data["Outcome (3pt)"] = outcome_count
                row_data.update(match_breakdowns)
                unified_data.append(row_data)
                
            df_unified = pd.DataFrame(unified_data).sort_values(by=["Total Points", "Exact (4pt)"], ascending=[False, False])
            
            filter_matches = st.multiselect("Filter by Specific Matches:", options=match_headers_list, placeholder="Showing all matches...")
            
            df_filtered = df_unified.copy()
            if filter_matches:
                keep_cols = ["Participant", "Total Points", "Exact (4pt)", "Outcome (3pt)"] + filter_matches
                df_filtered = df_filtered[keep_cols]
                
            st.dataframe(df_filtered, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.write("### 👀 See what others predicted")
            selected_p_name = st.selectbox("Select a participant to view their full prediction list:", options=[p["name"] for p in participants])
            
            target_row = next((row for row in unified_data if row["Participant"] == selected_p_name), None)
            if target_row:
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Pts", target_row["Total Points"])
                c2.metric("Exact Scores", target_row["Exact (4pt)"])
                c3.metric("Correct Outcomes", target_row["Outcome (3pt)"])
                
                with st.expander(f"View Full Match Matrix Cards for {selected_p_name}", expanded=True):
                    for m_header in match_headers_list:
                        st.markdown(f"**{m_header}**: `{target_row[m_header]}`")

# --- TAB: ENTER/UPDATE SCORES (ADMIN ONLY) ---
elif menu == "Enter/Update Scores":
    st.title("📝 Enter/Update Scores")
    participants = db.get("participants", [])
    fixtures = db.get("fixtures", [])
    
    if not participants:
        st.warning("No participants enrolled.")
    elif not fixtures:
        st.warning("No matches available.")
    else:
        part_dict = {p["id"]: p["name"] for p in participants}
        selected_id = st.selectbox("Select Profile:", list(part_dict.keys()), format_func=lambda x: part_dict[x])
        
        preds = db.get("predictions", [])
        saved_preds_dict = {(p["participantId"], p["fixtureId"]): p for p in preds}
        
        updated_preds = []
        locked_preds = []
        
        with st.form("prediction_submission_form", clear_on_submit=False):
            st.markdown(f"### Edit/Update Scores for: **{part_dict[selected_id]}**")
            
            # Separate fixtures into pending and finished
            pending_fixtures = [f for f in fixtures if f.get("status") != "FINISHED"]
            finished_fixtures = [f for f in fixtures if f.get("status") == "FINISHED"]
            
            # 1. Handle Finished Matches (Collapsible)
            if finished_fixtures:
                with st.expander("🟢 View Locked Predictions (Finished Matches)"):
                    for f in finished_fixtures:
                        curr_pred = saved_preds_dict.get((selected_id, f["id"]), None)
                        score_text = f"{curr_pred['scoreA']}-{curr_pred['scoreB']}" if curr_pred else "No prediction"
                        st.markdown(f"**{f['teamA']} vs {f['teamB']}**: `{score_text}`")
                        if curr_pred: 
                            locked_preds.append(curr_pred)
            
            # 2. Handle Pending Matches (Editable)
            st.markdown("---")
            st.markdown("### ⏳ Pending Predictions")
            for f in pending_fixtures:
                curr_pred = saved_preds_dict.get((selected_id, f["id"]), None)
                with st.container(border=True):
                    st.caption(f"{format_date(f['date'])}")
                    st.markdown(f"#### {get_flag(f['teamA'])} {f['teamA']} vs {f['teamB']} {get_flag(f['teamB'])}")
                    
                    col1, col2 = st.columns(2)
                    default_val_A = int(curr_pred["scoreA"]) if (curr_pred is not None and curr_pred.get("scoreA") is not None) else 0
                    default_val_B = int(curr_pred["scoreB"]) if (curr_pred is not None and curr_pred.get("scoreB") is not None) else 0
                    
                    val_A = col1.number_input(f"{f['teamA']} Score", min_value=0, max_value=20, value=default_val_A, key=f"predA_{f['id']}_{selected_id}")
                    val_B = col2.number_input(f"{f['teamB']} Score", min_value=0, max_value=20, value=default_val_B, key=f"predB_{f['id']}_{selected_id}")
                    updated_preds.append({"participantId": selected_id, "fixtureId": f["id"], "scoreA": val_A, "scoreB": val_B})
                
            if st.form_submit_button("💾 Save Pending Predictions", use_container_width=True):
                other_preds = [p for p in preds if p["participantId"] != selected_id]
                db["predictions"] = other_preds + locked_preds + updated_preds
                save_db(db)
                st.success(f"Updated successfully for {part_dict[selected_id]}!")
                st.rerun()

# --- TAB: MANAGE GAMES ---
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

    # Split matches into two lists
    fixtures = db.get("fixtures", [])
    pending = [f for f in fixtures if f["status"] == "PENDING"]
    finished = [f for f in fixtures if f["status"] == "FINISHED"]

    st.subheader("⏳ Pending Matches")
    if not pending:
        st.info("No pending games.")
    else:
        for f in pending:
            # Inline Edit Form (Placed before the container to handle re-rendering)
            if st.session_state.get(f"edit_mode_{f['id']}", False):
                with st.container(border=True):
                    st.write(f"### Editing: {f['teamA']} vs {f['teamB']}")
                    with st.form(f"edit_fixture_form_{f['id']}"):
                        teamA_edit = st.selectbox("Home Team", sorted(TEAMS), index=sorted(TEAMS).index(f["teamA"]))
                        teamB_edit = st.selectbox("Away Team", sorted(TEAMS), index=sorted(TEAMS).index(f["teamB"]))
                        phase_edit = st.text_input("Tournament Phase", f["phase"])
                        date_edit = st.date_input("Scheduled Date", value=datetime.strptime(f["date"], "%Y-%m-%d").date())
                        
                        col_save, col_cancel = st.columns(2)
                        if col_save.form_submit_button("✅ Save Changes"):
                            f.update({"teamA": teamA_edit, "teamB": teamB_edit, "phase": phase_edit, "date": str(date_edit)})
                            save_db(db)
                            st.session_state[f"edit_mode_{f['id']}"] = False
                            st.rerun()
                        if col_cancel.form_submit_button("❌ Cancel"):
                            st.session_state[f"edit_mode_{f['id']}"] = False
                            st.rerun()
                continue # Skip rendering the default view while editing

            # Default View
            with st.container(border=True):
                st.markdown(f"**{f['phase']}** | {format_date(f['date'])}")
                st.markdown(f"#### {get_flag(f['teamA'])} {f['teamA']} vs {f['teamB']} {get_flag(f['teamB'])}")
                
                col_sa, col_sb, col_btn = st.columns([1, 1, 1])
                with col_sa: 
                    val_sa = st.number_input(f"{f['teamA']} Score", min_value=0, max_value=20, value=f["scoreA"] or 0, key=f"sa_{f['id']}")
                with col_sb: 
                    val_sb = st.number_input(f"{f['teamB']} Score", min_value=0, max_value=20, value=f["scoreB"] or 0, key=f"sb_{f['id']}")
                with col_btn:
                    st.write("###") 
                    if st.button("✅ Finish Match", key=f"fin_{f['id']}", use_container_width=True, type="primary"):
                        f.update({"scoreA": val_sa, "scoreB": val_sb, "status": "FINISHED"})
                        save_db(db)
                        st.rerun()
                
                if st.button("✏️ Edit Details", key=f"edit_btn_{f['id']}"):
                    st.session_state[f"edit_mode_{f['id']}"] = True
                    st.rerun()

    st.subheader("🟢 Finished Matches")
    if not finished:
        st.info("No finished games.")
    else:
        with st.expander("View Concluded Matches"):
            for f in finished:
                st.markdown(f"**{f['teamA']} {f['scoreA']} - {f['scoreB']} {f['teamB']}** ({f['phase']})")
# --- TAB: PARTICIPANTS ---
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

# --- TAB: SHARE & EXPORT ---
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
                match_header = f"{f['teamA']} vs {f['teamB']} [{f['scoreA']}-{f['scoreB']}]" if is_finished else f"{f['teamA']} vs {f['teamB']} [Pending]"
                
                pred = next((pr for pr in p_preds if pr["fixtureId"] == f["id"]), None)
                if pred is not None and pred.get("scoreA") is not None and pred.get("scoreB") is not None:
                    pred_str = f"{pred['scoreA']}-{pred['scoreB']}"
                    if is_finished:
                        pts = compute_points(pred["scoreA"], pred["scoreB"], f["scoreA"], f["scoreB"])
                        if pts == 4: exact_count += 1
                        if pts >= 3: outcome_count += 1
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
            
        df_unified = pd.DataFrame(unified_data).sort_values(by=["Total Points", "Exact Scores (4pt)"], ascending=[False, False])
        
        st.subheader("📋 Performance Matrix")
        st.dataframe(df_unified, use_container_width=True)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_unified.to_excel(writer, sheet_name='Audit Report', index=False)
            
        st.download_button(
            label="📥 Download Excel (.xlsx)",
            data=output.getvalue(),
            file_name="Tournament_Audit_Log.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        st.download_button(
            label="📥 Download Backup (.json)",
            data=json.dumps(db, indent=4),
            file_name="system_data_backup.json",
            mime="application/json",
            use_container_width=True
        )