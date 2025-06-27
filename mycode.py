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



