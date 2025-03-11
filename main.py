import sqlite3
import pytz
import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from datetime import datetime

# Database Setup
conn = sqlite3.connect("pharmacy.db")
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS medicines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    stock INTEGER NOT NULL,
    expiry_date DATE NOT NULL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_name TEXT NOT NULL,
    medicine_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    date_taken DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()

# Get Manila Timezone
def get_manila_time():
    tz = pytz.timezone('Asia/Manila')
    return datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

# Set Log File Path
download_path = "/storage/emulated/0/Download"
log_file_path = os.path.join(download_path, "medicine_log.txt")

# Ensure Log File Exists
if not os.path.exists(log_file_path):
    try:
        with open(log_file_path, "w") as log_file:
            log_file.write("Medicine Dispense Log\n")
    except Exception as e:
        print(f"Error creating log file: {e}")

# Kivy App Class
class PharmacyApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical')

        # Add Medicine Section
        self.med_name = TextInput(hint_text="Name of Medicine")
        self.med_stock = TextInput(hint_text="Stock", input_filter='int')
        self.med_expiry = TextInput(hint_text="Expiry Date (YYYY-MM-DD)")
        self.add_button = Button(text="Add Medicine", on_press=self.add_medicine)

        # Dispense Medicine Section
        self.patient_name = TextInput(hint_text="Name of Patient")
        self.dispense_med = TextInput(hint_text="Name of Medicine")
        self.dispense_qty = TextInput(hint_text="Quantity Taken", input_filter='int')
        self.dispense_button = Button(text="Give Medicine", on_press=self.dispense_medicine)

        # Other Functions
        self.check_stock_button = Button(text="Show Stock", on_press=self.show_stock)
        self.check_expiry_button = Button(text="Check Expiry", on_press=self.check_expiry)
        self.view_logs_button = Button(text="Check Logs", on_press=self.view_logs)
        self.export_logs_button = Button(text="Export Log File", on_press=self.export_logs)

        # Add Widgets to Layout
        self.layout.add_widget(Label(text="Cabiao Senior High School"))

        self.layout.add_widget(Label(text="Add Medicine"))
        self.layout.add_widget(self.med_name)
        self.layout.add_widget(self.med_stock)
        self.layout.add_widget(self.med_expiry)
        self.layout.add_widget(self.add_button)

        self.layout.add_widget(Label(text="Give Medicine"))
        self.layout.add_widget(self.patient_name)
        self.layout.add_widget(self.dispense_med)
        self.layout.add_widget(self.dispense_qty)
        self.layout.add_widget(self.dispense_button)

        self.layout.add_widget(self.check_stock_button)
        self.layout.add_widget(self.check_expiry_button)
        self.layout.add_widget(self.view_logs_button)
        self.layout.add_widget(self.export_logs_button)

        return self.layout

    # Function to Add Medicine
    def add_medicine(self, instance):
        name = self.med_name.text
        stock = self.med_stock.text
        expiry = self.med_expiry.text

        if name and stock and expiry:
            cursor.execute("INSERT INTO medicines (name, stock, expiry_date) VALUES (?, ?, ?)", (name, int(stock), expiry))
            conn.commit()
            self.show_popup("Success", f"{name} added with {stock} stock!")
            self.med_name.text = ""
            self.med_stock.text = ""
            self.med_expiry.text = ""
        else:
            self.show_popup("Error", "Fill all fields!")

    # Function to Dispense Medicine
    def dispense_medicine(self, instance):
        patient = self.patient_name.text
        medicine = self.dispense_med.text
        quantity = self.dispense_qty.text

        cursor.execute("SELECT stock FROM medicines WHERE name = ?", (medicine,))
        result = cursor.fetchone()

        if result and patient and quantity:
            current_stock = result[0]
            if current_stock >= int(quantity):
                new_stock = current_stock - int(quantity)
                cursor.execute("UPDATE medicines SET stock = ? WHERE name = ?", (new_stock, medicine))
                cursor.execute("INSERT INTO logs (patient_name, medicine_name, quantity, date_taken) VALUES (?, ?, ?, ?)", 
                               (patient, medicine, int(quantity), get_manila_time()))
                conn.commit()

                # Save Log to File with Error Handling
                try:
                    with open(log_file_path, "a") as log_file:
                        log_file.write(f"{get_manila_time()} - {patient} took {quantity} {medicine}\n")
                except Exception as e:
                    self.show_popup("File Error", f"Could not write to log file:\n{e}")

                self.show_popup("Success", f"{patient} took {quantity} of {medicine}. Remaining stock: {new_stock}.")
                self.patient_name.text = ""
                self.dispense_med.text = ""
                self.dispense_qty.text = ""
            else:
                self.show_popup("Error", "Insufficient stock!")
        else:
            self.show_popup("Error", "Invalid input or medication not found!")

    # Function to Show Medicine Stock
    def show_stock(self, instance):
        cursor.execute("SELECT name, stock FROM medicines")
        medicines = cursor.fetchall()

        if medicines:
            stock_info = "\n".join([f"{name}: {stock} left" for name, stock in medicines])
        else:
            stock_info = "No medicines available."

        self.show_popup("Medicine Stock", stock_info)

    # Function to Check Expiry Dates
    def check_expiry(self, instance):
        today = datetime.today().strftime('%Y-%m-%d')
        cursor.execute("SELECT name, expiry_date FROM medicines WHERE expiry_date <= ?", (today,))
        expired_medicines = cursor.fetchall()

        if expired_medicines:
            expiry_info = "\n".join([f"{name} - Expired on {expiry}" for name, expiry in expired_medicines])
        else:
            expiry_info = "No expired medicines."

        self.show_popup("Expiry Check", expiry_info)

    # Function to View Logs
    def view_logs(self, instance):
        cursor.execute("SELECT patient_name, medicine_name, quantity, date_taken FROM logs ORDER BY date_taken DESC")
        logs = cursor.fetchall()

        if logs:
            log_list = "\n".join([f"{log[3]} - {log[0]} took {log[2]} of {log[1]}" for log in logs])
            self.show_popup("Medicine Logs", log_list)
        else:
            self.show_popup("No Logs", "No transactions have been recorded yet.")

    # Function to Export Logs to Storage
    def export_logs(self, instance):
        if os.path.exists(log_file_path):
            self.show_popup("Export Success", f"Log file saved in:\n{log_file_path}")
        else:
            self.show_popup("Export Failed", "No logs found to export.")

    # Function to Show Popup Messages
    def show_popup(self, title, message):
        popup_layout = BoxLayout(orientation='vertical')
        popup_label = Label(text=message)
        close_button = Button(text="OK", size_hint=(1, 0.3))

        popup_layout.add_widget(popup_label)
        popup_layout.add_widget(close_button)

        popup = Popup(title=title, content=popup_layout, size_hint=(0.8, 0.5))
        close_button.bind(on_press=popup.dismiss)
        popup.open()

# Run the App
if __name__ == "__main__":
    PharmacyApp().run()

# Close DB connection on exit
conn.close()