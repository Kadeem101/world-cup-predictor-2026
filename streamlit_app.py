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

def get_flag(team): return FLAGS.get(team, "⚽")
def format_date(date_str):
    try: return datetime.strptime(date_str, "%Y-%m-%d").strftime("%a. %d %B")
    except: return date_str
def format_time(time_str):
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
st.set_page_config(page_title="WC2026", layout="wide", initial_sidebar_state="collapsed")
db = load_db()
if "admin_authenticated" not in st.session_state: st.session_state.admin_authenticated = False

# --- NAVIGATION ---
view_mode = st.sidebar.selectbox("Access Level", ["👥 Public View", "🛡️ Admin Console"])

if view_mode == "🛡️ Admin Console" and not st.session_state.admin_authenticated:
    key = st.sidebar.text_input("Admin Key", type="password")
    if st.sidebar.button("Verify"):
        if key == "admin123":
            st.session_state.admin_authenticated = True
            st.rerun()
        else:
            st.sidebar.error("Invalid Key")

# Define menu based on state
options = ["Leaderboard", "My Predictions"]
if view_mode == "🛡️ Admin Console" and st.session_state.admin_authenticated:
    options += ["Manage Games", "Participants", "Share & Export"]

menu = st.sidebar.radio("Navigation", options)

# --- TABS ---
if menu == "Leaderboard":
    st.title("🏆 Leaderboard")
    # ... (Restored Leaderboard Logic)
    leader_rows = []
    for p in db.get("participants", []):
        total, exact, outcome, completed = 0, 0, 0, 0
        p_preds = [pr for pr in db.get("predictions", []) if pr["participantId"] == p["id"]]
        for pred in p_preds:
            fix = next((f for f in db.get("fixtures", []) if f["id"] == pred["fixtureId"]), None)
            if fix and fix.get("status") == "FINISHED":
                completed += 1
                pts = compute_points(pred["scoreA"], pred["scoreB"], fix["scoreA"], fix["scoreB"])
                if pts == 4: exact += 1
                if pts >= 3: outcome += 1
                total += pts
        leader_rows.append({"Competitor": p["name"], "Total Pts": total, "Exact (4)": exact, "Won (3)": outcome})
    
    if leader_rows:
        st.dataframe(pd.DataFrame(leader_rows).sort_values(by="Total Pts", ascending=False), use_container_width=True)

    st.subheader("🟢 Finished Matches")
    with st.expander("Show/Hide Completed Matches"):
        for f in [f for f in db.get("fixtures", []) if f["status"] == "FINISHED"]:
            st.markdown(f"{get_flag(f['teamA'])} {f['teamA']} **{f['scoreA']}-{f['scoreB']}** {f['teamB']} {get_flag(f['teamB'])}")

    st.subheader("⏳ Upcoming")
    for f in [f for f in db.get("fixtures", []) if f["status"] == "PENDING"]:
        with st.container(border=True):
            st.caption(f"{format_date(f['date'])} | {format_time(f['time'])}")
            st.markdown(f"{get_flag(f['teamA'])} {f['teamA']} vs {get_flag(f['teamB'])} {f['teamB']}")

elif menu == "My Predictions":
    # ... (Restored My Predictions Logic)
    st.title("📝 My Predictions")
    part_dict = {p["id"]: p["name"] for p in db.get("participants", [])}
    selected_id = st.selectbox("Select Profile:", list(part_dict.keys()), format_func=lambda x: part_dict[x])
    preds = {(p["participantId"], p["fixtureId"]): p for p in db.get("predictions", [])}
    for f in db.get("fixtures", []):
        curr = preds.get((selected_id, f["id"]))
        with st.container(border=True):
            st.caption(f"{format_date(f['date'])}")
            st.markdown(f"**{get_flag(f['teamA'])} {f['teamA']} vs {get_flag(f['teamB'])} {f['teamB']}**")
            if curr and curr.get('scoreA') is not None:
                st.write(f"Prediction: {get_flag(f['teamA'])} {curr['scoreA']} - {curr['scoreB']} {get_flag(f['teamB'])}")
            else:
                st.info("No prediction logged")

elif menu == "Manage Games":
    st.title("⚙️ Manage Games")
    # ... (Your previous Match Controller logic here)
elif menu == "Participants":
    st.title("👥 Participants")
    # ... (Your previous Participant logic here)
elif menu == "Share & Export":
    st.title("📤 Share & Export")
    # ... (Your previous Export logic here)