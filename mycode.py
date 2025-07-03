# Child Vaccination Schedule Assistant 

import streamlit as st
import pandas as pd
import sqlite3
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from fpdf import FPDF
from io import BytesIO
import plotly.express as px
from twilio.rest import Client
import hashlib
import base64
import textwrap

# ============================
# Twilio Setup (Update credentials before deployment)
# ============================
TWILIO_SID = "your_twilio_account_sid"
TWILIO_AUTH_TOKEN = "your_twilio_auth_token"
TWILIO_FROM = "+1234567890"  # Twilio phone number
client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

# ============================
# App Configuration
# ============================
st.set_page_config(page_title="Child Vaccination Assistant", layout="wide")

# ============================
# Database Setup
# ============================
DB_FILE = 'members.db'

def init_db():
    import os
    st.write("🔍 Using DB file:", os.path.abspath(DB_FILE))

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            dob TEXT NOT NULL,
            gender TEXT,
            residence TEXT,
            phone TEXT,
            vaccines TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            vaccine TEXT,
            date TEXT,
            notes TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            pin TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ============================
# Load KEPI Vaccine Schedule JSON
# ============================
with open("vaccine_info.json", "r") as f:
    vaccine_data = json.load(f)

# ✅ Safe conversion from list to dict if necessary
if isinstance(vaccine_data, list):
    try:
        vaccine_data = {v['name']: v for v in vaccine_data if isinstance(v, dict) and 'name' in v}
    except Exception as e:
        st.error("❌ Error processing vaccine_info.json. Please check its format.")
        st.stop()

elif not isinstance(vaccine_data, dict):
    st.error("❌ vaccine_info.json must be a list of vaccine dicts or a dict.")
    st.stop()

kepi_schedule = {
    "BCG": ["0 weeks"],
    "OPV": ["0 weeks", "6 weeks", "10 weeks", "14 weeks"],
    "Rotavirus": ["6 weeks", "10 weeks"],
    "Pneumo_conj": ["6 weeks", "10 weeks", "14 weeks"],
    "DTwPHibHepB": ["6 weeks", "10 weeks", "14 weeks"],
    "IPV": ["14 weeks"],
    "Yellow Fever": ["9 months"],
    "Measles": ["9 months", "18 months"],
    "HPV": ["10 years", "10 years 6 months"]
}

# ============================
# PIN Protection (Email + PIN with Hashing)
# ============================
def hash_pin(pin):
    return hashlib.sha256(pin.encode()).hexdigest()

def check_pin():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    # 🔐 Main screen introduction
    st.title("🔐 Welcome to the Child Vaccination Assistant")
    st.markdown("""
    This secure platform is designed to help **healthcare providers** and **parents**:
    - Register children for routine immunizations
    - Track upcoming and completed vaccines
    - Log post-vaccination side effects
    - Learn more about each vaccine

    👉 Please **log in** or **register** using your email and a 6-digit PIN to get started.
    """)

    # 🔒 Sidebar input
    st.sidebar.subheader("Login or Register")
    auth_mode = st.sidebar.radio("Choose Action", ["Login", "Register"])
    email = st.sidebar.text_input("📧 Email")
    pin = st.sidebar.text_input("🔑 6-digit PIN", type="password")
    remember = st.sidebar.checkbox("Remember Me")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    if auth_mode == "Register":
        pin_confirm = st.sidebar.text_input("🔁 Repeat PIN", type="password")
        if st.sidebar.button("✅ Register"):
            if len(pin) != 6 or not pin.isdigit():
                st.sidebar.error("PIN must be a 6-digit number.")
            elif pin != pin_confirm:
                st.sidebar.error("PINs do not match.")
            else:
                try:
                    hashed = hash_pin(pin)
                    c.execute("INSERT INTO users (email, pin) VALUES (?, ?)", (email, hashed))
                    conn.commit()
                    st.sidebar.success("Registration successful. Please log in.")
                except sqlite3.IntegrityError:
                    st.sidebar.error("Email already registered.")

    elif auth_mode == "Login":
        if st.sidebar.button("🔓 Login"):
            hashed = hash_pin(pin)
            c.execute("SELECT * FROM users WHERE email=? AND pin=?", (email, hashed))
            result = c.fetchone()
            if result:
                st.session_state.authenticated = True
                st.session_state.user_email = email
                st.sidebar.success(f"Welcome back, {email.split('@')[0].title()}!")
                return True
            else:
                st.sidebar.error("Invalid email or PIN.")

    conn.close()
    return False

# 🔐 Stop page if not logged in
if not check_pin():
    st.stop()

# ============================
# Sidebar Menu
# ============================
menu = st.sidebar.radio("🌟 Navigate", [
    "🏠 Dashboard",
    "➕ Register Child",
    "📚 Vaccine Info",
    "📆 Vaccination Status",
    "📝 Reaction Logs",
    "🤖 Vaccine Assistant",
    "👥 View Members",
    "📤 Export Report"
])


# ============================
# Register Child
# ============================
def register_member():
    st.header("➕ Register New Child")
    with st.form("register"):
        name = st.text_input("Child's Name")
        dob = st.date_input("Date of Birth")
        gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        residence = st.text_input("Residence / Village")
        phone = st.text_input("Guardian Phone Number")
        submit = st.form_submit_button("Register")

        if submit and name:
            # ✅ Prefill all vaccines with False
            default_vaccine_status = {}
            for v, times in kepi_schedule.items():
                for t in times:
                    default_vaccine_status[f"{v} - {t}"] = False

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute(
                "INSERT INTO members (name, dob, gender, residence, phone, vaccines) VALUES (?, ?, ?, ?, ?, ?)",
                (name, dob.isoformat(), gender, residence, phone, json.dumps(default_vaccine_status))
            )
            conn.commit()
            conn.close()
            st.success("✅ Registered Successfully!")


# ============================
# ============================
# View Members
# ============================
def view_members():
    st.header("👥 All Registered Members")

    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM members", conn)
    conn.close()

    if df.empty:
        st.info("No registered members found.")
        return

    # Show formatted table
    st.subheader("📋 Member Table")
    st.dataframe(df)

    # Show raw vaccine JSON for debugging
    st.subheader("🔬 Raw Vaccine JSON Data")
    for _, row in df.iterrows():
        st.write(f"{row['name']} - {row['vaccines']}")


# ============================
# Vaccine Info
# ============================
def view_vaccine_info():
    st.header("📚 KEPI Vaccine Information")
    for vaccine, details in vaccine_data.items():
        with st.expander(vaccine):
            st.write(f"📅 **Scheduled Age:** {details.get('Scheduled Age', 'N/A')}")
            st.write(f"🛡 **Protects Against:** {details.get('Protects Against', 'N/A')}")
            st.write(f"🧬 **Type:** {details.get('Type', 'N/A')}")
            st.write(f"💉 **Route:** {details.get('Route', 'N/A')}")
            st.write("💊 **Side Effects:**")
            for effect in details.get('Common Side Effects', []):
                st.markdown(f"- {effect}")
            st.write("⚠️ **Special Notes:**")
            for note in details.get('Special Considerations', []):
                st.markdown(f"- {note}")

# ============================
# Vaccination Tracker
# ============================
def track_vaccines():
    st.header("📆 Track Vaccination")
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM members", conn)
    conn.close()
    if df.empty:
        st.warning("No children registered yet.")
        return

    selected = st.selectbox("Select Child", df["name"])
    row = df[df["name"] == selected].iloc[0]
    dob = datetime.strptime(row["dob"], "%Y-%m-%d")
    try:
        vaccine_status = json.loads(row["vaccines"] or "{}")
    except json.JSONDecodeError:
        st.error("❌ Could not decode vaccine data. Resetting to empty.")
        vaccine_status = {}

    today = datetime.today().date()

    updated = {}
    for v, times in kepi_schedule.items():
        for t in times:
            due = dob + (
                relativedelta(weeks=int(t.split()[0])) if "week" in t else
                relativedelta(months=int(t.split()[0])) if "month" in t else
                relativedelta(years=int(t.split()[0]))
            )
            key = f"{v} - {t}"
            taken_flag = vaccine_status.get(key, False)
            updated[key] = st.checkbox(f"{v} ({t}) - Due {due.date()}", value=bool(taken_flag))


    if st.button("💾 Save Status"):
        st.write("Saving for:", selected)
        st.write("Row ID:", row["id"])

        # Merge new updates with existing data
        merged_status = vaccine_status.copy()
        merged_status.update(updated)

        st.write("🧬 Merged Status JSON:")
        st.json(merged_status)  # Debug: shows what you're saving

        try:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("UPDATE members SET vaccines=? WHERE id=?", (json.dumps(merged_status), row["id"]))
            conn.commit()
            conn.close()
            st.success("✅ Vaccination Status Updated & Saved")
        except Exception as e:
            st.error(f"❌ Failed to save data: {e}")




# ============================
# Reaction Logs
# ============================
def reaction_logs():
    st.header("📝 Post-Vaccination Reaction Log")
    conn = sqlite3.connect(DB_FILE)
    members = pd.read_sql_query("SELECT * FROM members", conn)
    conn.close()
    if members.empty:
        st.warning("No children available.")
        return

    with st.form("reaction_form"):
        child = st.selectbox("Select Child", members["name"])
        vaccine = st.text_input("Vaccine Name")
        date = st.date_input("Date of Reaction")
        notes = st.text_area("Reaction Notes")
        submit = st.form_submit_button("Log Reaction")

        if submit:
            mid = members[members["name"] == child].iloc[0]["id"]
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("INSERT INTO reactions (member_id, vaccine, date, notes) VALUES (?, ?, ?, ?)",
                      (mid, vaccine, date.isoformat(), notes))
            conn.commit()
            conn.close()
            st.success("✅ Reaction Logged")

# ============================
# Export to PDF
# ============================
def export_to_pdf():
    st.header("📄 Export Registered Children to PDF")
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM members", conn)
    conn.close()

    if df.empty:
        st.info("No data to export.")
        return

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Registered Children Report", ln=True, align='C')

    for index, row in df.iterrows():
        pdf.cell(200, 10, txt=f"{row['name']} | DOB: {row['dob']} | Gender: {row['gender']} | Residence: {row['residence']}", ln=True)

    buffer = BytesIO()
    pdf.output(buffer)
    st.download_button("📥 Download PDF", data=buffer.getvalue(), file_name="registered_children.pdf", mime="application/pdf")

# ============================
# Trends Chart
# ============================
def show_trends_chart():
    st.header("📊 Vaccination Trends")
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM members", conn)
    conn.close()

    if df.empty:
        st.info("No data to visualize.")
        return

    df['dob'] = pd.to_datetime(df['dob'])
    df['year'] = df['dob'].dt.year

    fig = px.histogram(df, x='year', title="Registered Children by Birth Year")
    st.plotly_chart(fig, use_container_width=True)

# ============================
# AI Vaccine Assistant
# ============================
def vaccine_assistant():
    st.header("🤖 AI Vaccine Assistant")

    # Load vaccine data from vaccine_info.json
    try:
        with open("vaccine_info.json", "r") as f:
            vaccine_data = json.load(f)
    except Exception as e:
        st.error("❌ Failed to load vaccine_info.json. Please ensure the file exists and is correctly formatted.")
        return

    question = st.text_input("Ask a question about any vaccine (e.g., 'Tell me about BCG' or 'What does HPV protect against?')")

    if question:
        matched = None

        # Try to find the vaccine name in the question
        for vax_name in vaccine_data:
            if vax_name.lower() in question.lower():
                matched = vax_name
                break

        if matched:
            data = vaccine_data[matched]
            st.success(f"💉 Vaccine: **{matched}**")
            st.write(f"📅 **Scheduled Age**: {data.get('Scheduled Age', 'N/A')}")

            # Supports both string and list for "Protects Against"
            protection = data.get("Protects Against", "N/A")
            if isinstance(protection, list):
                st.write("🛡 **Protects Against:**")
                for item in protection:
                    st.markdown(f"- {item}")
            else:
                st.write(f"🛡 **Protects Against:** {protection}")

            st.write(f"🧬 **Type**: {data.get('Type', 'N/A')}")
            st.write(f"💉 **Route**: {data.get('Route', 'N/A')}")

            # Side effects
            side_effects = data.get("Common Side Effects", [])
            if side_effects:
                st.write("💊 **Common Side Effects:**")
                for effect in side_effects:
                    st.markdown(f"- {effect}")
            else:
                st.write("💊 No side effects listed.")

            # Special notes
            notes = data.get("Special Considerations", [])
            if notes:
                st.write("⚠️ **Special Considerations:**")
                for note in notes:
                    st.markdown(f"- {note}")
            else:
                st.write("⚠️ No special considerations.")
        else:
            st.warning("🤔 Sorry, I couldn't find info for that. Please try using the exact name like 'BCG', 'Measles', or 'HPV'.")





# ============================
# Dashboard
# ============================
def show_dashboard():
    st.title("📊 Dashboard Overview")
    st.markdown("""
    Welcome to the **Dashboard Overview** of the Child Vaccination Assistant.  
    Here you can quickly monitor vaccination activity, see upcoming or overdue doses, and get a summary of all registered children.
    """)

    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM members", conn)
    conn.close()
    if df.empty:
        st.info("No data to display.")
        return

    total = len(df)
    today = datetime.today().date()
    upcoming7 = overdue = completed = 0

    for _, row in df.iterrows():
        dob = datetime.strptime(row["dob"], "%Y-%m-%d")
        status = json.loads(row["vaccines"] or "{}")
        for v, times in kepi_schedule.items():
            for t in times:
                due = dob + (
                    relativedelta(weeks=int(t.split()[0])) if "week" in t else
                    relativedelta(months=int(t.split()[0])) if "month" in t else
                    relativedelta(years=int(t.split()[0]))
                )
                key = f"{v} - {t}"
                if due.date() == today:
                    completed += 1
                elif due.date() < today and not status.get(key):
                    overdue += 1
                elif today <= due.date() <= today + timedelta(days=7):
                    upcoming7 += 1

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("👶 Registered", total)
    col2.metric("💉 Due Today", completed)
    col3.metric("📆 Next 7 Days", upcoming7)
    col4.metric("✅ Completed", sum(1 for v in status.values() if v))
    col5.metric("⚠️ Overdue", overdue)

# ============================
# Export Vaccine Completion Report with Filters and PDF
# ============================
def export_vaccine_report():
    st.header("📤 Export Completed Vaccines Report")

    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM members", conn)
    conn.close()

    if df.empty:
        st.warning("No registered members found.")
        return

    df["dob"] = pd.to_datetime(df["dob"])
    df["age"] = df["dob"].apply(lambda x: (datetime.today().date() - x.date()).days // 365)

    # === Filter Section ===
    with st.expander("🔍 Filter Options", expanded=True):
        residences = sorted(df["residence"].dropna().unique().tolist())
        selected_residence = st.multiselect("Filter by Residence", residences)

        dob_min, dob_max = st.date_input("Filter by Date of Birth Range", value=[df["dob"].min().date(), df["dob"].max().date()])

        age_range = st.slider("Filter by Age (Years)", 0, 18, (0, 18))

    # === Apply Filters ===
    filtered_df = df.copy()

    selected_names = st.multiselect("Filter by Child Name", options=df["name"].unique())

    if selected_names:
        filtered_df = filtered_df[filtered_df["name"].isin(selected_names)]

    filtered_df = filtered_df[
        (filtered_df["dob"].dt.date >= dob_min) &
        (filtered_df["dob"].dt.date <= dob_max) &
        (filtered_df["age"] >= age_range[0]) &
        (filtered_df["age"] <= age_range[1])
    ]

    if filtered_df.empty:
        st.warning("No members match the selected filters.")
        return

    # === Prepare Report Data ===
    report_data = []

    for _, row in filtered_df.iterrows():
        name = row.get("name", "N/A")
        dob = pd.to_datetime(row.get("dob", None)).date() if row.get("dob") else "Unknown"
        residence = row.get("residence", "Unknown")

        # Safely load vaccines JSON from DB
        try:
            vaccines = json.loads(row["vaccines"] or "{}")
        except (json.JSONDecodeError, TypeError):
            st.warning(f"⚠️ Skipping {name} due to invalid vaccine data.")
            vaccines = {}

        # Extract completed vaccines
        completed = [key.split(" - ")[0] for key, val in vaccines.items() if str(val).lower() in ("true", "1", "yes")]
        unique_completed = sorted(set(completed))

        # Append row to report
        report_data.append({
            "Name": name,
            "Date of Birth": str(dob),
            "Residence": residence,
            "Completed Vaccines": ", ".join(unique_completed) if unique_completed else "None"
        })

    # Convert to DataFrame
    report_df = pd.DataFrame(report_data)
    st.dataframe(report_df)

    # === CSV Export ===
    csv = report_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download CSV", data=csv, file_name="completed_vaccines_report.csv", mime='text/csv')

    # === PDF Export ===
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(190, 10, txt="Completed Vaccines Report", ln=True, align='C')
    pdf.ln(10)

    for row in report_data:
        line = f"{row['Name']} | DOB: {row['Date of Birth']} | Residence: {row['Residence']} | Completed: {row['Completed Vaccines']}"
        wrapped_lines = textwrap.wrap(line, width=90)  # Wrap at 90 chars

        for wrapped_line in wrapped_lines:
            pdf.multi_cell(0, 10, wrapped_line, align='L')

        pdf.ln(2)  # Add spacing between entries

    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)

    st.download_button("📥 Download PDF", data=buffer.getvalue(), file_name="completed_vaccines_report.pdf", mime="application/pdf")
# ============================
# Route Pages
# ============================
if menu == "🏠 Dashboard":
    show_dashboard()
elif menu == "➕ Register Child":
    register_member()
elif menu == "📚 Vaccine Info":
    view_vaccine_info()
elif menu == "📆 Vaccination Status":
    track_vaccines()
elif menu == "📝 Reaction Logs":
    reaction_logs()
elif menu == "🤖 Vaccine Assistant":
    vaccine_assistant()
elif menu == "👥 View Members":
    view_members()
elif menu == "📤 Export Report":
    export_vaccine_report()

