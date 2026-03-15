import sys
import joblib
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QComboBox, QSlider, QRadioButton, QButtonGroup,
                             QPushButton, QGroupBox, QProgressBar, QTextEdit, QSplitter,
                             QScrollArea, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor

# Load the model
model = joblib.load('best_tuned_model.joblib')
all_features = model.feature_names_in_

class FraudDetectionApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Transaction Analysis & Fraud Detection")
        self.setGeometry(100, 100, 1200, 800)
        
        # Set up the main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # Create splitter for sidebar and main content
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Sidebar for inputs
        self.sidebar = self.create_sidebar()
        splitter.addWidget(self.sidebar)
        
        # Main content area
        self.main_content = self.create_main_content()
        splitter.addWidget(self.main_content)
        
        # Set splitter proportions
        splitter.setSizes([400, 800])
        
        # Apply modern styling
        self.apply_styling()
    
    def create_sidebar(self):
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout = QVBoxLayout(scroll_widget)
        
        # Title
        title = QLabel("📝 Transaction Details")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)
        
        # Numerical Inputs
        num_group = QGroupBox("Numerical Details")
        num_layout = QVBoxLayout(num_group)
        
        self.amount_input = self.create_labeled_input("Transaction Amount (₹):", "100.0", num_layout)
        self.freq_input = self.create_labeled_input("Transaction Frequency:", "1", num_layout)
        self.deviation_input = self.create_labeled_input("Transaction Amount Deviation:", "0.0", num_layout)
        self.days_input = self.create_labeled_input("Days Since Last Transaction:", "0", num_layout)
        
        layout.addWidget(num_group)
        
        # Time Inputs
        time_group = QGroupBox("⏰ Time Details")
        time_layout = QVBoxLayout(time_group)
        
        # Hour slider
        hour_layout = QHBoxLayout()
        hour_layout.addWidget(QLabel("Hour of Day:"))
        self.hour_slider = QSlider(Qt.Horizontal)
        self.hour_slider.setRange(0, 23)
        self.hour_slider.setValue(12)
        self.hour_label = QLabel("12")
        self.hour_slider.valueChanged.connect(lambda v: self.hour_label.setText(str(v)))
        hour_layout.addWidget(self.hour_slider)
        hour_layout.addWidget(self.hour_label)
        time_layout.addLayout(hour_layout)
        
        # Day slider
        day_layout = QHBoxLayout()
        day_layout.addWidget(QLabel("Day of Week (0=Mon, 6=Sun):"))
        self.day_slider = QSlider(Qt.Horizontal)
        self.day_slider.setRange(0, 6)
        self.day_slider.setValue(0)
        self.day_label = QLabel("0")
        self.day_slider.valueChanged.connect(lambda v: self.day_label.setText(str(v)))
        day_layout.addWidget(self.day_slider)
        day_layout.addWidget(self.day_label)
        time_layout.addLayout(day_layout)
        
        # Month slider
        month_layout = QHBoxLayout()
        month_layout.addWidget(QLabel("Month (1-12):"))
        self.month_slider = QSlider(Qt.Horizontal)
        self.month_slider.setRange(1, 12)
        self.month_slider.setValue(1)
        self.month_label = QLabel("1")
        self.month_slider.valueChanged.connect(lambda v: self.month_label.setText(str(v)))
        month_layout.addWidget(self.month_slider)
        month_layout.addWidget(self.month_label)
        time_layout.addLayout(month_layout)
        
        layout.addWidget(time_group)
        
        # Categorical Inputs
        cat_group = QGroupBox("Categorical Details")
        cat_layout = QVBoxLayout(cat_group)
        
        self.trans_type_combo = self.create_labeled_combo("Transaction Type:", 
            ["Bill Payment", "Investment", "Other", "Purchase", "Refund", "Subscription"], cat_layout)
        self.gateway_combo = self.create_labeled_combo("Payment Gateway:", 
            ["Bank of Data", "CReditPAY", "Dummy Bank", "Gamma Bank", "Other", "SamplePay", "Sigma Bank", "UPI Pay"], cat_layout)
        self.device_combo = self.create_labeled_combo("Device OS:", 
            ["MacOS", "Windows", "iOS"], cat_layout)
        self.merchant_combo = self.create_labeled_combo("Merchant Category:", 
            ["Donations and Devotion", "Financial services and Taxes", "Home delivery", "Investment", "More Services", "Other", "Purchases", "Travel bookings", "Utilities"], cat_layout)
        
        # Channel radio buttons
        channel_layout = QHBoxLayout()
        channel_layout.addWidget(QLabel("Channel:"))
        self.channel_group = QButtonGroup()
        self.mobile_radio = QRadioButton("Mobile")
        self.online_radio = QRadioButton("Online")
        self.online_radio.setChecked(True)
        self.channel_group.addButton(self.mobile_radio)
        self.channel_group.addButton(self.online_radio)
        channel_layout.addWidget(self.mobile_radio)
        channel_layout.addWidget(self.online_radio)
        channel_layout.addStretch()
        cat_layout.addLayout(channel_layout)
        
        layout.addWidget(cat_group)
        
        # Location Inputs
        loc_group = QGroupBox("Location Details")
        loc_layout = QVBoxLayout(loc_group)
        
        state_options = [s.replace("Transaction_State_", "") for s in all_features if "Transaction_State_" in s]
        self.state_combo = self.create_labeled_combo("Transaction State:", state_options, loc_layout)
        
        city_options = [c.replace("Transaction_City_", "") for c in all_features if "Transaction_City_" in c]
        self.city_combo = self.create_labeled_combo("Transaction City:", city_options, loc_layout)
        
        layout.addWidget(loc_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.analyze_button = QPushButton("Analyze Transaction")
        self.analyze_button.clicked.connect(self.analyze_transaction)
        
        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(self.reset_inputs)
        
        button_layout.addWidget(self.analyze_button)
        button_layout.addWidget(self.reset_button)
        layout.addLayout(button_layout)
        
        layout.addStretch()
        return scroll_area
    
    def create_main_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Header
        header = QLabel("Transaction Analysis & Fraud Detection")
        header.setFont(QFont("Segoe UI", 22, QFont.DemiBold))
        header.setStyleSheet("""
            QLabel {
                color: #111827;
                padding: 18px;
                border-radius: 12px;
                background: #ffffff;
                border: 1px solid rgba(0,0,0,0.08);
            }
        """)
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Result area
        result_group = QGroupBox("📊 Analysis Result")
        result_layout = QVBoxLayout(result_group)
        
        self.result_label = QLabel("Enter details and click 'Analyze Transaction'")
        self.result_label.setFont(QFont("Arial", 16))
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet("""
            QLabel {
                padding: 20px;
                border-radius: 10px;
                background: rgba(255,255,255,0.1);
                color: #333;
            }
        """)
        result_layout.addWidget(self.result_label)
        
        self.confidence_label = QLabel("")
        self.confidence_label.setFont(QFont("Arial", 14))
        self.confidence_label.setAlignment(Qt.AlignCenter)
        result_layout.addWidget(self.confidence_label)
        
        self.confidence_bar = QProgressBar()
        self.confidence_bar.setRange(0, 100)
        self.confidence_bar.setValue(0)
        result_layout.addWidget(self.confidence_bar)
        
        layout.addWidget(result_group)
        
        # Progress area
        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Details area
        details_group = QGroupBox("📈 Detailed Probabilities")
        details_layout = QVBoxLayout(details_group)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        details_layout.addWidget(self.details_text)
        
        layout.addWidget(details_group)
        
        layout.addStretch()
        return widget
    
    def create_labeled_input(self, label_text, default_value, parent_layout):
        layout = QHBoxLayout()
        layout.addWidget(QLabel(label_text))
        input_field = QLineEdit(default_value)
        layout.addWidget(input_field)
        parent_layout.addLayout(layout)
        return input_field
    
    def create_labeled_combo(self, label_text, options, parent_layout):
        layout = QHBoxLayout()
        layout.addWidget(QLabel(label_text))
        combo = QComboBox()
        combo.addItems(options)
        layout.addWidget(combo)
        parent_layout.addLayout(layout)
        return combo
    
    def apply_styling(self):
        self.setStyleSheet("""
            QMainWindow {
                background: #f4f6f8;
            }
            QWidget {
                font-family: "Segoe UI", "Calibri", sans-serif;
            }
            QLabel {
                color: #1f2937;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid rgba(0,0,0,0.12);
                border-radius: 12px;
                margin-top: 14px;
                background: #ffffff;
                padding: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
            }
            QLineEdit, QComboBox {
                background: #ffffff;
                border: 1px solid rgba(0,0,0,0.16);
                border-radius: 8px;
                padding: 6px 10px;
                min-height: 28px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #2563eb;
            }
            QPushButton {
                background: #2563eb;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #1d4ed8;
            }
            QPushButton:pressed {
                background: #1e40af;
            }
            QProgressBar {
                border-radius: 10px;
                background: rgba(0,0,0,0.06);
                height: 16px;
            }
            QProgressBar::chunk {
                background: #2563eb;
                border-radius: 10px;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            QSlider::groove:horizontal {
                border: 1px solid rgba(0,0,0,0.12);
                height: 8px;
                background: rgba(0,0,0,0.1);
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #2563eb;
                border: 1px solid rgba(0,0,0,0.2);
                width: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }
        """)
    
    def analyze_transaction(self):
        try:
            # Update progress
            self.progress_label.setText("🔄 Analyzing transaction...")
            self.progress_bar.setValue(25)
            QApplication.processEvents()
            
            # Collect inputs
            amount = float(self.amount_input.text())
            freq = int(self.freq_input.text())
            deviation = float(self.deviation_input.text())
            days_since = int(self.days_input.text())
            hour = self.hour_slider.value()
            day = self.day_slider.value()
            month = self.month_slider.value()
            
            trans_type = self.trans_type_combo.currentText()
            gateway = self.gateway_combo.currentText()
            device = self.device_combo.currentText()
            merchant = self.merchant_combo.currentText()
            channel = "Mobile" if self.mobile_radio.isChecked() else "Online"
            state = self.state_combo.currentText()
            city = self.city_combo.currentText()
            
            self.progress_bar.setValue(50)
            self.progress_label.setText("📊 Preparing data...")
            QApplication.processEvents()
            
            # Create input dataframe
            input_df = pd.DataFrame(np.zeros((1, len(all_features))), columns=all_features)
            
            # Fill numerical values
            input_df['amount'] = amount
            input_df['Transaction_Frequency'] = freq
            input_df['Transaction_Amount_Deviation'] = deviation
            input_df['Days_Since_Last_Transaction'] = days_since
            input_df['Hour'] = hour
            input_df['Day_of_Week'] = day
            input_df['Month'] = month
            
            # Fill categorical values
            if f"Transaction_Type_{trans_type}" in all_features:
                input_df[f"Transaction_Type_{trans_type}"] = 1
            if f"Payment_Gateway_{gateway}" in all_features:
                input_df[f"Payment_Gateway_{gateway}"] = 1
            if f"Device_OS_{device}" in all_features:
                input_df[f"Device_OS_{device}"] = 1
            if f"Merchant_Category_{merchant}" in all_features:
                input_df[f"Merchant_Category_{merchant}"] = 1
            if f"Transaction_Channel_{channel}" in all_features:
                input_df[f"Transaction_Channel_{channel}"] = 1
            if f"Transaction_State_{state}" in all_features:
                input_df[f"Transaction_State_{state}"] = 1
            if f"Transaction_City_{city}" in all_features:
                input_df[f"Transaction_City_{city}"] = 1
            
            self.progress_bar.setValue(75)
            self.progress_label.setText("🤖 Running prediction...")
            QApplication.processEvents()
            
            # Make prediction
            prediction = model.predict(input_df)
            proba = model.predict_proba(input_df)
            
            self.progress_bar.setValue(100)
            self.progress_label.setText("✅ Analysis complete!")
            QApplication.processEvents()
            
            # Update results
            class_label = "Fraud" if prediction[0] == 1 else "Not Fraud"
            confidence = max(proba[0]) * 100
            
            if prediction[0] == 1:
                self.result_label.setStyleSheet("""
                    QLabel {
                        color: #e74c3c;
                        font-weight: bold;
                        font-size: 18px;
                        padding: 20px;
                        border-radius: 10px;
                        background: rgba(231, 76, 60, 0.2);
                    }
                """)
                self.result_label.setText(f"⚠️ FRAUD DETECTED\nPredicted: {class_label}")
            else:
                self.result_label.setStyleSheet("""
                    QLabel {
                        color: #27ae60;
                        font-weight: bold;
                        font-size: 18px;
                        padding: 20px;
                        border-radius: 10px;
                        background: rgba(39, 174, 96, 0.2);
                    }
                """)
                self.result_label.setText(f"✅ LEGITIMATE TRANSACTION\nPredicted: {class_label}")
            
            self.confidence_label.setText(f"Confidence: {confidence:.2f}%")
            self.confidence_bar.setValue(int(confidence))
            
            # Update details
            details = f"Prediction Probabilities:\n\n"
            details += f"Not Fraud: {proba[0][0]*100:.2f}%\n"
            details += f"Fraud: {proba[0][1]*100:.2f}%\n\n"
            details += f"Input Summary:\n"
            details += f"Amount: ₹{amount}\n"
            details += f"Type: {trans_type}\n"
            details += f"Gateway: {gateway}\n"
            details += f"Device: {device}\n"
            details += f"Channel: {channel}\n"
            details += f"Location: {city}, {state}"
            
            self.details_text.setText(details)
            
            # Clear progress after a delay
            QTimer.singleShot(2000, lambda: self.clear_progress())
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred during analysis:\n{str(e)}")
            self.clear_progress()
    
    def clear_progress(self):
        self.progress_bar.setValue(0)
        self.progress_label.setText("")
    
    def reset_inputs(self):
        # Reset numerical inputs
        self.amount_input.setText("100.0")
        self.freq_input.setText("1")
        self.deviation_input.setText("0.0")
        self.days_input.setText("0")
        
        # Reset sliders
        self.hour_slider.setValue(12)
        self.day_slider.setValue(0)
        self.month_slider.setValue(1)
        
        # Reset combos to first item
        self.trans_type_combo.setCurrentIndex(0)
        self.gateway_combo.setCurrentIndex(0)
        self.device_combo.setCurrentIndex(0)
        self.merchant_combo.setCurrentIndex(0)
        self.state_combo.setCurrentIndex(0)
        self.city_combo.setCurrentIndex(0)
        
        # Reset radio
        self.online_radio.setChecked(True)
        
        # Clear results
        self.result_label.setText("Enter details and click 'Analyze Transaction'")
        self.result_label.setStyleSheet("""
            QLabel {
                padding: 20px;
                border-radius: 10px;
                background: rgba(255,255,255,0.1);
                color: #333;
            }
        """)
        self.confidence_label.setText("")
        self.confidence_bar.setValue(0)
        self.details_text.clear()
        self.clear_progress()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FraudDetectionApp()
    window.show()
    sys.exit(app.exec_())