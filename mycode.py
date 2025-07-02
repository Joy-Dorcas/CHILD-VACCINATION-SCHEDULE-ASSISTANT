# Child Vaccination Assistant - Enhanced Streamlit App (Final + Fixed)

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

    st.sidebar.subheader("🔐 Secure Access")

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

if not check_pin():
    st.stop()

# ============================
# Sidebar Menu
# ============================
menu = st.sidebar.radio("🌟 Navigate", [
    "🏠 Dashboard",
    "➕ Register Child",
    "👥 View Members",
    "📚 Vaccine Info",
    "📆 Vaccination Status",
    "📝 Reaction Logs",
    "🤖 Vaccine Assistant"
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
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("INSERT INTO members (name, dob, gender, residence, phone, vaccines) VALUES (?, ?, ?, ?, ?, ?)",
                      (name, dob.isoformat(), gender, residence, phone, json.dumps({})))
            conn.commit()
            conn.close()
            st.success("✅ Registered Successfully!")

# ============================
# View Members
# ============================
def view_members():
    st.header("👥 All Registered Members")
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM members", conn)
    conn.close()
    st.dataframe(df)

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
    vaccine_status = json.loads(row["vaccines"] or "{}")
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
            updated[key] = st.checkbox(f"{v} ({t}) - Due {due.date()}", value=taken_flag)

    if st.button("💾 Save Status"):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("UPDATE members SET vaccines=? WHERE id=?", (json.dumps(updated), row["id"]))
        conn.commit()
        conn.close()
        st.success("✅ Status Updated")

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
# Route Pages
# ============================
if menu == "🏠 Dashboard":
    show_dashboard()
elif menu == "➕ Register Child":
    register_member()
elif menu == "👥 View Members":
    view_members()
elif menu == "📚 Vaccine Info":
    view_vaccine_info()
elif menu == "📆 Vaccination Status":
    track_vaccines()
elif menu == "📝 Reaction Logs":
    reaction_logs()
elif menu == "🤖 Vaccine Assistant":
    vaccine_assistant()





# Child Vaccination Schedule Assistant - Full Enhanced Version
# Author: Joy Dorcas (with ChatGPT support)

import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
from tkcalendar import Calendar
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json, os, uuid, csv
from fpdf import FPDF
from twilio.rest import Client

# --- CONFIGURATION --- #
DATA_FILE = "user_data.json"
VACCINE_INFO_FILE = "vaccine_info.json"
PIN_FILE = "user_pin.json"
TWILIO_FILE = "twilio_config.json"

# --- STATIC VACCINE DATA --- #
vaccine_schedule = {
    "BCG": ["0 weeks"],
    "OPV": ["0 weeks", "6 weeks", "10 weeks", "14 weeks"],
    "Rotavirus": ["6 weeks", "10 weeks"],
    "Pneumo_conj": ["6 weeks", "10 weeks", "14 weeks"],
    "DTwPHibHepB": ["6 weeks", "10 weeks", "14 weeks"],
    "IPV": ["14 weeks"],
    "Yellow Fever": ["9 months"],
    "Measles": ["9 months", "18 months"],
    "HPV": ["10 years", "10 years 6 months"],
    "HepB_Adult": ["18 years"],
    "TT": ["5 years"],
    "Typhoid": ["2 years"]
}

vaccine_info = {
    "BCG": {"importance": "Protects against severe forms of TB.", "reactions": "Swelling, mild fever, scar."},
    "OPV": {"importance": "Prevents polio.", "reactions": "Mild diarrhea, rare vaccine-derived polio."},
    "Rotavirus": {"importance": "Prevents rotavirus diarrhea.", "reactions": "Mild diarrhea, vomiting."},
    "Pneumo_conj": {"importance": "Protects against pneumonia & meningitis.", "reactions": "Swelling, fever."},
    "DTwPHibHepB": {"importance": "Combo vaccine for 5 diseases.", "reactions": "Fever, rash, swelling."},
    "IPV": {"importance": "Inactivated polio vaccine.", "reactions": "Soreness, mild fever."},
    "Yellow Fever": {"importance": "Prevents yellow fever.", "reactions": "Fever, aches, allergy."},
    "Measles": {"importance": "Prevents measles.", "reactions": "Rash, fever, seizures (rare)."},
    "HPV": {"importance": "Prevents cervical cancer.", "reactions": "Dizziness, swelling."},
    "HepB_Adult": {"importance": "Protects liver from hepatitis B.", "reactions": "Tiredness, pain."},
    "TT": {"importance": "Prevents tetanus.", "reactions": "Muscle soreness, fever."},
    "Typhoid": {"importance": "Prevents typhoid.", "reactions": "Fever, headache."}
}

# --- LOAD/SAVE UTILITIES --- #
def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    else:
        with open(path, 'w') as f:
            json.dump(default, f, indent=4)
        return default

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)

def calculate_due(dob):
    due = {}
    for vac, times in vaccine_schedule.items():
        due[vac] = []
        for t in times:
            num, unit = int(t.split()[0]), t.split()[1]
            date = dob + (relativedelta(weeks=num) if 'week' in unit else
                          relativedelta(months=num) if 'month' in unit else
                          relativedelta(years=num))
            due[vac].append(date.strftime("%Y-%m-%d"))
    return due

def send_sms(to, message):
    creds = load_json(TWILIO_FILE, {"account_sid": "", "auth_token": "", "from_number": ""})
    if not all(creds.values()):
        messagebox.showerror("Twilio Error", "Twilio credentials not configured.")
        return
    try:
        client = Client(creds['account_sid'], creds['auth_token'])
        client.messages.create(body=message, from_=creds['from_number'], to=to)
        messagebox.showinfo("Success", f"Reminder sent to {to}")
    except Exception as e:
        messagebox.showerror("SMS Failed", str(e))

# --- GUI ROOT --- #
root = tk.Tk()
root.title("Vaccination Assistant")
root.geometry("1024x700")
canvas = tk.Canvas(root)
scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
frame = tk.Frame(canvas)
frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.create_window((0, 0), window=frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)
canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

user_data = load_json(DATA_FILE, {})
pin_data = load_json(PIN_FILE, {})

# --- PIN AUTH --- #
def pin_auth():
    login = tk.Toplevel()
    login.title("PIN Authentication")
    login.geometry("300x150")
    login.grab_set()  # Focus on the PIN window
    login.resizable(False, False)

    tk.Label(login, text="Enter PIN:", font=("Arial", 12)).pack(pady=10)
    pin_entry = tk.Entry(login, show="*", font=("Arial", 12), width=20, justify='center')
    pin_entry.pack(pady=5)
    pin_entry.focus_set()

    def verify():
        entered = pin_entry.get()
        if 'pin' not in pin_data:
            if len(entered) >= 4:
                pin_data['pin'] = entered
                save_json(PIN_FILE, pin_data)
                login.destroy()
                build_app()
            else:
                messagebox.showerror("Error", "PIN must be at least 4 digits.")
        elif entered == pin_data['pin']:
            login.destroy()
            build_app()
        else:
            messagebox.showerror("Error", "Wrong PIN")

    tk.Button(login, text="Continue", command=verify, width=10).pack(pady=10)


# --- APP --- #
def build_app():
    entries = {}
    form = tk.LabelFrame(frame, text="Register Child")
    form.pack(fill="x", pady=5)
    fields = ["Name", "Date of Birth (YYYY-MM-DD)", "Gender", "Weight", "Conditions", "Phone"]
    for i, f in enumerate(fields):
        tk.Label(form, text=f).grid(row=i, column=0)
        entry = tk.Entry(form, width=40)
        entry.grid(row=i, column=1)
        entries[f] = entry

    def register():
        try:
            dob = datetime.strptime(entries["Date of Birth (YYYY-MM-DD)"].get(), "%Y-%m-%d")
        except:
            messagebox.showerror("Error", "Invalid DOB format")
            return
        name = entries['Name'].get()
        if any(child['name'] == name for child in user_data.values()):
            messagebox.showinfo("Exists", "Child already registered")
            return
        cid = str(uuid.uuid4())
        user_data[cid] = {
            "name": name,
            "dob": entries["Date of Birth (YYYY-MM-DD)"].get(),
            "gender": entries["Gender"].get(),
            "weight": entries["Weight"].get(),
            "conditions": entries["Conditions"].get(),
            "phone": entries["Phone"].get(),
            "vaccines": calculate_due(dob),
            "completed": {},
            "reactions": {}
        }
        save_json(DATA_FILE, user_data)
        messagebox.showinfo("Success", f"{name} registered successfully.")
        display_dashboard(cid)

    tk.Button(form, text="Register", command=register).grid(row=len(fields), column=1, pady=5)

    def display_dashboard(cid):
        child = user_data[cid]
        dash = tk.LabelFrame(frame, text=f"Dashboard: {child['name']}")
        dash.pack(fill="x", pady=5)

        for vac, dates in child['vaccines'].items():
            for d in dates:
                color = "green" if vac in child['completed'] and d in child['completed'][vac] else (
                         "orange" if datetime.strptime(d, "%Y-%m-%d") > datetime.today() else "red")
                status = "✔" if color == "green" else "✘"
                row = tk.Frame(dash)
                row.pack(anchor="w")
                tk.Label(row, text=f"{vac}: {d} - {status}", fg=color).pack(side="left")
                tk.Button(row, text="Info", command=lambda v=vac: show_info(v)).pack(side="left")
                tk.Button(row, text="✔", command=lambda v=vac, d=d: mark_complete(cid, v, d)).pack(side="left")
                tk.Button(row, text="Reaction", command=lambda v=vac: reaction_log(cid, v)).pack(side="left")

        tk.Button(dash, text="Export PDF", command=lambda: export_pdf(cid)).pack()
        tk.Button(dash, text="Export CSV", command=lambda: export_csv(cid)).pack()
        tk.Button(dash, text="Calendar", command=calendar_popup).pack()
        tk.Button(dash, text="AI Assistant", command=chatbot).pack()
        tk.Button(dash, text="Send SMS", command=lambda: send_sms(child['phone'], f"Upcoming vaccines for {child['name']}"))

    def show_info(vac):
        info = vaccine_info.get(vac, {})
        messagebox.showinfo(f"{vac} Info", f"Importance: {info.get('importance')}\nReactions: {info.get('reactions')}")

    def mark_complete(cid, vac, date):
        user_data[cid]['completed'].setdefault(vac, []).append(date)
        save_json(DATA_FILE, user_data)
        messagebox.showinfo("Done", f"Marked {vac} as completed.")

    def reaction_log(cid, vac):
        win = tk.Toplevel()
        win.title(f"Reaction to {vac}")
        text = ScrolledText(win, width=40, height=5)
        text.pack()
        def save():
            user_data[cid]['reactions'][vac] = text.get("1.0", "end").strip()
            save_json(DATA_FILE, user_data)
            messagebox.showinfo("Saved", "Reaction recorded. Call 0800-123-456 in emergency.")
            win.destroy()
        tk.Button(win, text="Save", command=save).pack(pady=5)

    def export_pdf(cid):
        try:
            child = user_data[cid]
            filename = f"{child['name'].replace(' ', '_')}_vaccines.pdf"
            
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            
            pdf.cell(0, 10, txt=f"Vaccine Report for {child['name']}", ln=True, align="C")
            pdf.ln(10)

            # Table Header
            pdf.set_font("Arial", "B", size=12)
            pdf.cell(60, 10, "Vaccine", border=1)
            pdf.cell(60, 10, "Date", border=1)
            pdf.cell(60, 10, "Status", border=1)
            pdf.ln()

            # Table Body
            pdf.set_font("Arial", size=11)
            for vac, dates in child["vaccines"].items():
                for d in dates:
                    status = "Completed" if vac in child["completed"] and d in child["completed"][vac] else "Pending"
                    pdf.cell(60, 10, vac, border=1)
                    pdf.cell(60, 10, d, border=1)
                    pdf.cell(60, 10, status, border=1)
                    pdf.ln()

            pdf.output(filename)
            messagebox.showinfo("PDF Exported", f"File saved as:\n{filename}")
        
        except Exception as e:
            messagebox.showerror("Export Error", f"Could not export PDF.\n\n{str(e)}")



    def export_csv(cid):
        child = user_data[cid]
        with open(f"{child['name'].replace(' ', '_')}_vaccines.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Vaccine", "Date", "Status"])
            for vac, dates in child['vaccines'].items():
                for d in dates:
                    status = "Completed" if vac in child['completed'] and d in child['completed'][vac] else "Pending"
                    writer.writerow([vac, d, status])

    def calendar_popup():
        top = tk.Toplevel()
        top.title("Vaccine Calendar")
        Calendar(top, selectmode='day').pack(pady=10)

    def chatbot():
        win = tk.Toplevel()
        win.title("Vaccine AI Assistant")
        tk.Label(win, text="Ask about a vaccine:").pack()
        entry = tk.Entry(win, width=50)
        entry.pack()
        out = ScrolledText(win, height=10)
        out.pack()
        def reply():
            query = entry.get().lower()
            for v in vaccine_info:
                if v.lower() in query:
                    i = vaccine_info[v]['importance']
                    r = vaccine_info[v]['reactions']
                    out.insert("end", f"{v}:\nImportance: {i}\nReactions: {r}\n\n")
                    return
            out.insert("end", "Please ask about a valid vaccine.\n")
        tk.Button(win, text="Ask", command=reply).pack(pady=5)

pin_auth()
root.mainloop()



