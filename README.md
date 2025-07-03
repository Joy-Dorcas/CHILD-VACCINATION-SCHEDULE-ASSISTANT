# 🧒💉 Child Vaccination Assistant - Streamlit App

A secure and feature-rich web application built with **Streamlit** to help healthcare providers and parents manage child immunization schedules, track vaccine completion, record post-vaccination reactions, and generate insightful reports.

---

## 📌 Features

✅ **PIN-Protected Login System**  
- Secure login and registration using email and hashed 6-digit PIN.  
- "Remember Me" functionality for session persistence.

✅ **Dashboard Overview**  
- Real-time stats: registered children, doses due today, upcoming, completed, and overdue.

✅ **Child Registration**  
- Register new children with details like name, date of birth, gender, residence, and guardian’s phone number.

✅ **Vaccine Tracker**  
- Calculates due dates based on Kenya’s KEPI schedule.  
- Check off completed vaccines and save updates.

✅ **Vaccine Info Explorer**  
- View detailed data from `vaccine_info.json`:  
  - Scheduled age  
  - What it protects against  
  - Vaccine type and route  
  - Side effects and special considerations

✅ **Post-Vaccination Reaction Logging**  
- Record adverse reactions by child, vaccine, and date.

✅ **AI Vaccine Assistant 🤖**  
- Ask questions like:
  - “Tell me about BCG”
  - “What does HPV protect against?”  
- Powered by simple keyword matching with structured JSON data.

✅ **Export Tools**  
- Download completed vaccination reports as **PDF** or **CSV**  
- Apply filters by name, DOB, age range, and residence.

✅ **Vaccination Trends Visualization**  
- See child registration trends using Plotly histograms.

✅ **SMS Notification Ready**  
- Easily integrate Twilio to send SMS reminders for upcoming vaccines.

---

## 🗂️ Project Structure

📁 your_project_directory/
├── app.py # Main Streamlit app script
├── members.db # SQLite database
├── vaccine_info.json # Vaccine data source
├── README.md # This file


---

## 🚀 Getting Started

### 🔧 Requirements

- Python 3.8+
- Streamlit
- pandas, fpdf, sqlite3, plotly, twilio, dateutil

### 📦 Setup

```bash
# Clone the project
git clone https://github.com/yourusername/child-vaccine-assistant.git
cd child-vaccine-assistant

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
🧬 vaccine_info.json Format
json
Copy
Edit
{
  "BCG": {
    "Scheduled Age": "0 weeks",
    "Protects Against": ["Tuberculosis"],
    "Type": "Live Attenuated",
    "Route": "Intradermal",
    "Common Side Effects": ["Swelling", "Fever"],
    "Special Considerations": ["Do not give to immunocompromised children"]
  }
}
🔐 Twilio Integration (Optional)
Replace the following in app.py with your actual Twilio credentials:

python
Copy
Edit
TWILIO_SID = "your_twilio_account_sid"
TWILIO_AUTH_TOKEN = "your_twilio_auth_token"
TWILIO_FROM = "+1234567890"
▶️ Run the App
bash
Copy
Edit
streamlit run app.py
💡 Use Cases
Health clinics tracking childhood immunizations

Parents keeping vaccination records

NGO community health projects

Public health data collection and reporting

🛡️ Security
PINs are hashed using SHA-256 before storage

All data stored locally in a SQLite database

Designed for single-clinic or personal use; security enhancements recommended for public deployments

📜 License
MIT License
Free for personal or commercial use. Attribution is appreciated.

👩‍💻 Author
Child Vaccination Assistant developed by Joy Dorcas
Email: joymanyara55@gmail.com
