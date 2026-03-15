import os
import json
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
import re
from io import BytesIO

from flask import Flask, jsonify, render_template, request, send_file
import joblib
import numpy as np

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from flask_socketio import SocketIO, emit
import random
import requests
import io
import csv

# Image processing imports
from PIL import Image
import pytesseract
import cv2

# Configure Tesseract path for Windows
import platform
if platform.system() == 'Windows':
    # Try default PATH first
    try:
        pytesseract.pytesseract.get_tesseract_version()
        print("[INFO] Tesseract OCR found in PATH")
    except Exception:
        # If not in PATH, try common installation locations
        import os
        tesseract_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            os.path.expanduser(r'~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'),
            r'C:\Users\Asus\Downloads\tesseract.exe',  # User's custom installation
        ]
        for tesseract_path in tesseract_paths:
            if os.path.exists(tesseract_path):
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                print(f"[INFO] Using Tesseract from: {tesseract_path}")
                break
        else:
            print("[WARNING] Tesseract OCR not found. Screenshot analysis will be limited.")
            print("[INFO] Install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki")

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, '..', 'best_tuned_model.joblib')

# Email configuration
EMAIL_ENABLED = os.getenv('EMAIL_ENABLED', 'false').lower() == 'true'
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS', '')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
ALERT_EMAIL = os.getenv('ALERT_EMAIL', '')

# SMS configuration (using Twilio)
SMS_ENABLED = os.getenv('SMS_ENABLED', 'false').lower() == 'true'
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')
ALERT_PHONE_NUMBER = os.getenv('ALERT_PHONE_NUMBER', '')

# Load model once at startup
try:
    model = joblib.load(MODEL_PATH)
    # Get feature names if available (for sklearn models)
    if hasattr(model, 'feature_names_in_'):
        all_features = list(model.feature_names_in_)
    elif hasattr(model, 'n_features_in_'):
        all_features = model.n_features_in_
    else:
        all_features = None
    print(f"[OK] Loaded ML model: {type(model).__name__}")
    if all_features:
        if isinstance(all_features, list):
            print(f"[INFO] Model features: {len(all_features)} features")
        else:
            print(f"[INFO] Model expects: {all_features} features")
except Exception as e:
    print(f"[ERROR] Could not load ML model: {e}")
    model = None
    all_features = None

# -----------------------------------------------------------------------------


def _send_email_alert(transaction_data, result):
    """Send email alert for high-risk fraud transactions"""
    if not EMAIL_ENABLED or not EMAIL_ADDRESS or not ALERT_EMAIL:
        return False
    
    try:
        subject = f"🚨 High Fraud Risk Alert - ₹{transaction_data.get('amount', 0)}"
        
        body = f"""
        <html>
        <body>
            <h2 style="color: #ef4444;">🚨 Fraud Alert Detected</h2>
            <p><strong>A suspicious transaction has been flagged:</strong></p>
            
            <table style="border-collapse: collapse; width: 100%; margin: 20px 0;">
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Amount</strong></td><td style="padding: 8px; border: 1px solid #ddd;">₹{transaction_data.get('amount', 0)}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Transaction Type</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{transaction_data.get('trans_type', 'N/A')}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Fraud Probability</strong></td><td style="padding: 8px; border: 1px solid #ddd; color: #ef4444;">{result['proba_fraud']}%</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Confidence</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{result['confidence']}%</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Location</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{result['location']['city']}, {result['location']['country']}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Time</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{result['timestamp']}</td></tr>
            </table>
            
            <p><strong>Risk Factors:</strong></p>
            <ul>
                {''.join(f'<li>{factor}</li>' for factor in result.get('risk_factors', [])[:5])}
            </ul>
            
            <p style="color: #6b7280; font-size: 12px;">This is an automated alert from FINFENCE Fraud Detection System.</p>
        </body>
        </html>
        """
        
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = ALERT_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"[EMAIL] Alert sent to {ALERT_EMAIL}")
        return True
    except Exception as e:
        print(f"[EMAIL] Error sending alert: {e}")
        return False


def _send_sms_alert(transaction_data, result):
    """Send SMS alert for high-risk fraud transactions using Twilio"""
    if not SMS_ENABLED or not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        return False
    
    try:
        from twilio.rest import Client
        
        message_body = (
            f"🚨 FRAUD ALERT: ₹{transaction_data.get('amount', 0)} transaction flagged as {result['label']}. "
            f"Confidence: {result['confidence']}%. Location: {result['location']['city']}. "
            f"Check FINFENCE dashboard for details."
        )
        
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message_body,
            from_=TWILIO_PHONE_NUMBER,
            to=ALERT_PHONE_NUMBER
        )
        
        print(f"[SMS] Alert sent to {ALERT_PHONE_NUMBER}")
        return True
    except ImportError:
        print("[SMS] Twilio not installed. Run: pip install twilio")
        return False
    except Exception as e:
        print(f"[SMS] Error sending alert: {e}")
        return False


# -----------------------------------------------------------------------------
# Screenshot Analyzer Functions
# -----------------------------------------------------------------------------


def _extract_upi_details_from_text(text: str) -> dict:
    """Extract UPI transaction details from OCR text"""
    details = {
        'amount': None,
        'date': None,
        'time': None,
        'transaction_id': None,
        'sender': None,
        'receiver': None,
        'phone_number': None,
        'status': None
    }
    
    # Extract amount (₹ symbol or Rs/INR)
    amount_patterns = [
        r'₹\s*([\d,]+\.?\d*)',
        r'Rs\.?\s*([\d,]+\.?\d*)',
        r'INR\s*([\d,]+\.?\d*)',
        r'Amount:\s*₹?\s*([\d,]+\.?\d*)'
    ]
    for pattern in amount_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            details['amount'] = float(amount_str)
            break
    
    # Extract date
    date_patterns = [
        r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        r'(\d{1,2}\s+\w+\s+\d{4})',
        r'(\w+\s+\d{1,2},?\s+\d{4})'
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            details['date'] = match.group(1)
            break
    
    # Extract time
    time_patterns = [
        r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))',
        r'(\d{1,2}:\d{2}:\d{2})'
    ]
    for pattern in time_patterns:
        match = re.search(pattern, text)
        if match:
            details['time'] = match.group(1)
            break
    
    # Extract transaction ID
    txn_patterns = [
        r'Transaction\s+ID:\s*(\w+)',
        r'UTR:\s*(\w+)',
        r'Ref\s+No:\s*(\w+)'
    ]
    for pattern in txn_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            details['transaction_id'] = match.group(1)
            break
    
    # Extract phone number
    phone_match = re.search(r'\+?(\d{10,13})', text.replace(' ', '').replace('-', ''))
    if phone_match:
        details['phone_number'] = phone_match.group(1)
    
    # Extract status
    status_keywords = ['success', 'failed', 'pending', 'completed']
    for keyword in status_keywords:
        if keyword.lower() in text.lower():
            details['status'] = keyword.capitalize()
            break
    
    return details


def _detect_image_manipulation(image_bytes: bytes) -> dict:
    """Detect if screenshot has been manipulated/faked"""
    try:
        # Convert to OpenCV format
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return {'is_manipulated': False, 'confidence': 0, 'reasons': ['Could not process image']}
        
        manipulation_score = 0
        reasons = []
        
        # 1. Check for compression artifacts (sign of multiple saves/edits)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < 50:  # Low variance suggests heavy compression
            manipulation_score += 0.2
            reasons.append('Heavy compression detected')
        
        # 2. Check for inconsistent lighting/shadows
        edges = cv2.Canny(gray, 100, 200)
        edge_density = np.sum(edges > 0) / edges.size
        if edge_density > 0.3:  # Unusually high edge density
            manipulation_score += 0.15
            reasons.append('Unusual edge patterns')
        
        # 3. Check for text inconsistencies (different fonts/sizes)
        # This is a simplified check - real implementation would use ML
        height, width = gray.shape[:2]
        aspect_ratio = width / height
        
        # Standard screenshot aspect ratios
        if not (0.5 < aspect_ratio < 2.5):
            manipulation_score += 0.1
            reasons.append('Unusual image dimensions')
        
        # 4. Check for color histogram anomalies
        hist_b = cv2.calcHist([img], [0], None, [256], [0, 256])
        hist_g = cv2.calcHist([img], [1], None, [256], [0, 256])
        hist_r = cv2.calcHist([img], [2], None, [256], [0, 256])
        
        # Check for gaps in histogram (sign of editing)
        total_bins = len(hist_b)
        zero_bins_b = np.sum(hist_b == 0) / total_bins
        zero_bins_g = np.sum(hist_g == 0) / total_bins
        zero_bins_r = np.sum(hist_r == 0) / total_bins
        
        avg_zero_bins = (zero_bins_b + zero_bins_g + zero_bins_r) / 3
        if avg_zero_bins > 0.7:  # Many missing color values
            manipulation_score += 0.25
            reasons.append('Color histogram anomalies')
        
        # 5. Check for metadata inconsistencies (if available)
        # Note: PIL/Pillow can extract EXIF data
        
        # Final determination
        is_manipulated = manipulation_score > 0.4
        confidence = min(manipulation_score * 100, 100)
        
        return {
            'is_manipulated': is_manipulated,
            'confidence': round(confidence, 1),
            'reasons': reasons if reasons else ['No significant manipulation detected'],
            'manipulation_score': round(manipulation_score, 2)
        }
        
    except Exception as e:
        print(f"[MANIPULATION] Error: {e}")
        return {
            'is_manipulated': False,
            'confidence': 0,
            'reasons': [f'Analysis error: {str(e)}']
        }


def _analyze_screenshot(image_file) -> dict:
    """Main function to analyze UPI payment screenshot"""
    try:
        # Read image
        image_bytes = image_file.read()
        image = Image.open(BytesIO(image_bytes))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Perform OCR
        text = pytesseract.image_to_string(image)
        
        # Extract UPI details
        extracted_details = _extract_upi_details_from_text(text)
        
        # Detect manipulation
        manipulation_analysis = _detect_image_manipulation(image_bytes)
        
        # Calculate authenticity score
        authenticity_score = 100 - manipulation_analysis['confidence']
        
        # Risk assessment
        risk_level = 'Low'
        if manipulation_analysis['is_manipulated']:
            risk_level = 'High'
        elif extracted_details['amount'] and extracted_details['amount'] > 50000:
            risk_level = 'Medium'
        
        # Generate summary
        summary_parts = []
        if extracted_details['amount']:
            summary_parts.append(f"Amount: ₹{extracted_details['amount']}")
        if extracted_details['status']:
            summary_parts.append(f"Status: {extracted_details['status']}")
        if extracted_details['transaction_id']:
            summary_parts.append(f"Txn ID: {extracted_details['transaction_id']}")
        
        result = {
            'success': True,
            'extracted_data': extracted_details,
            'manipulation_detected': manipulation_analysis['is_manipulated'],
            'manipulation_confidence': manipulation_analysis['confidence'],
            'authenticity_score': round(authenticity_score, 1),
            'risk_level': risk_level,
            'summary': ' | '.join(summary_parts) if summary_parts else 'Limited data extracted',
            'warnings': manipulation_analysis['reasons'],
            'ocr_text_length': len(text),
            'image_dimensions': {
                'width': image.width,
                'height': image.height
            }
        }
        
        print(f"[SCREENSHOT] Analysis complete: Risk={risk_level}, Authenticity={authenticity_score}%")
        return result
        
    except Exception as e:
        print(f"[SCREENSHOT] Error: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to analyze screenshot'
        }


def _extract_ml_features(data: dict) -> list:
    """Extract features for ML model prediction with proper encoding"""
    features = []
    
    # Basic numerical features
    features.extend([
        float(data.get('amount', 0)),
        float(data.get('oldbalanceOrg', 0)),
        float(data.get('newbalanceOrig', 0)),
        float(data.get('oldbalanceDest', 0)),
        float(data.get('newbalanceDest', 0)),
        int(data.get('frequency', 0)),
        float(data.get('deviation', 0)),
        int(data.get('days_since', 0)),
        int(data.get('hour', 0)),
        int(data.get('day', 0)),
        int(data.get('month', 1))
    ])
    
    # Transaction type one-hot encoding
    trans_types = ['Bill Payment', 'Investment', 'Other', 'Purchase', 'Refund', 'Subscription']
    for t_type in trans_types:
        features.append(1 if data.get('trans_type') == t_type else 0)
    
    # Gateway one-hot encoding
    gateways = ['Bank of Data', 'CReditPAY', 'Dummy Bank', 'Gamma Bank', 'Other', 'SamplePay', 'Sigma Bank', 'UPI Pay']
    for g_type in gateways:
        features.append(1 if data.get('gateway') == g_type else 0)
    
    # Device one-hot encoding
    devices = ['MacOS', 'Windows', 'iOS', 'Android']
    for d_type in devices:
        features.append(1 if data.get('device') == d_type else 0)
    
    # Merchant one-hot encoding
    merchants = ['Donations and Devotion', 'Financial services and Taxes', 'Home delivery', 'Investment', 'More Services', 'Other', 'Purchases', 'Travel bookings', 'Utilities']
    for m_type in merchants:
        features.append(1 if data.get('merchant') == m_type else 0)
    
    return features


def _advanced_rule_based_prediction(data: dict) -> tuple:
    """Advanced rule-based fraud detection with weighted scoring"""
    score = 0.0
    reasons = []
    
    amount = float(data.get('amount', 0))
    frequency = int(data.get('frequency', 0))
    deviation = float(data.get('deviation', 0))
    days_since = int(data.get('days_since', 0))
    hour = int(data.get('hour', 0))
    
    # Amount-based scoring (0-40 points)
    if amount > 100000:
        score += 35
        reasons.append("Very high transaction amount")
    elif amount > 50000:
        score += 25
        reasons.append("High transaction amount")
    elif amount > 25000:
        score += 15
        reasons.append("Moderately high amount")
    elif amount < 100:
        score += 5
        reasons.append("Unusually small amount")
    
    # Frequency-based scoring (0-25 points)
    if frequency > 20:
        score += 25
        reasons.append("Extremely high transaction frequency")
    elif frequency > 10:
        score += 18
        reasons.append("Very high transaction frequency")
    elif frequency > 5:
        score += 12
        reasons.append("High transaction frequency")
    elif frequency == 0:
        score += 8
        reasons.append("First transaction from this pattern")
    
    # Deviation-based scoring (0-20 points)
    if deviation > 0.9:
        score += 20
        reasons.append("Extreme deviation from normal behavior")
    elif deviation > 0.7:
        score += 15
        reasons.append("High deviation from normal behavior")
    elif deviation > 0.5:
        score += 10
        reasons.append("Moderate deviation from normal behavior")
    
    # Time-based scoring (0-10 points)
    if hour >= 22 or hour <= 5:
        score += 8
        reasons.append("Late night transaction")
    elif hour >= 20 or hour <= 7:
        score += 5
        reasons.append("Unusual transaction time")
    
    # Days since last transaction (0-10 points)
    if days_since > 90:
        score += 10
        reasons.append("Very long time since last transaction")
    elif days_since > 30:
        score += 7
        reasons.append("Long time since last transaction")
    elif days_since > 7:
        score += 3
        reasons.append("Some time since last transaction")
    
    # Transaction type risk (0-5 points)
    trans_type = data.get('trans_type', '')
    if trans_type in ['Investment', 'Other']:
        score += 5
        reasons.append("High-risk transaction type")
    
    # Device risk (0-3 points)
    device = data.get('device', '')
    if device in ['Unknown', 'Other']:
        score += 3
        reasons.append("Unknown device type")
    
    # Gateway risk (0-2 points)
    gateway = data.get('gateway', '')
    if gateway in ['Other', 'Dummy Bank']:
        score += 2
        reasons.append("Unusual payment gateway")
    
    # Convert score to probability (0-100 scale)
    fraud_probability = min(score / 100, 1.0)
    legitimate_probability = 1.0 - fraud_probability
    
    prediction = 1 if fraud_probability > 0.5 else 0
    
    return prediction, [legitimate_probability, fraud_probability], reasons


def _create_enhanced_description(data: dict) -> str:
    """Create detailed description for AI analysis"""
    amount = float(data.get('amount', 0))
    frequency = int(data.get('frequency', 0))
    deviation = float(data.get('deviation', 0))
    hour = int(data.get('hour', 0))
    
    risk_indicators = []
    
    if amount > 50000:
        risk_indicators.append("large amount")
    if frequency > 5:
        risk_indicators.append("high frequency")
    if deviation > 0.5:
        risk_indicators.append("unusual pattern")
    if hour >= 22 or hour <= 5:
        risk_indicators.append("late night timing")
    
    risk_text = f" with {' and '.join(risk_indicators)}" if risk_indicators else ""
    
    return (
        f"Financial transaction analysis: ₹{amount} transaction{risk_text}. "
        f"Account balance changed from ₹{data.get('oldbalanceOrg', 0)} to ₹{data.get('newbalanceOrig', 0)}. "
        f"Recipient balance from ₹{data.get('oldbalanceDest', 0)} to ₹{data.get('newbalanceDest', 0)}. "
        f"Transaction details: {data.get('trans_type', '')} via {data.get('gateway', '')} on {data.get('device', '')} device. "
        f"Merchant: {data.get('merchant', '')}. Location: {data.get('city', '')}, {data.get('state', '')}. "
        f"Pattern analysis: {frequency} transactions, {deviation:.2f} deviation, {data.get('days_since', 0)} days since last transaction. "
        f"Time: {hour}:00 on day {data.get('day', 0)} of month {data.get('month', 1)}. "
        f"Determine if this shows fraudulent activity."
    )


# -----------------------------------------------------------------------------


# Hugging Face API for zero-shot classification
HF_API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"
HF_TOKEN = os.getenv("HF_TOKEN")  # Set this environment variable with your Hugging Face token

# Hugging Face API for conversational AI
HF_CHAT_URL = "https://api-inference.huggingface.co/models/distilgpt2"

# In-memory transaction history for demo purposes
transaction_history = []
MAX_HISTORY = 100

# Add some demo transactions on startup for hackathon demo
def _add_demo_transactions():
    """Add demo transactions to make the dashboard look impressive"""
    demo_transactions = [
        {
            'amount': 5200, 'frequency': 3, 'deviation': 0.15, 'days_since': 1, 'hour': 10,
            'day': 2, 'month': 3, 'trans_type': 'Purchase', 'gateway': 'UPI Pay',
            'device': 'Android', 'merchant': 'Purchases', 'channel': 'Mobile',
            'state': 'Maharashtra', 'city': 'Mumbai', 'ip': '101.0.0.1'
        },
        {
            'amount': 12500, 'frequency': 8, 'deviation': 0.45, 'days_since': 3, 'hour': 14,
            'day': 3, 'month': 3, 'trans_type': 'Bill Payment', 'gateway': 'Sigma Bank',
            'device': 'iOS', 'merchant': 'Utilities', 'channel': 'Online',
            'state': 'Delhi', 'city': 'Delhi', 'ip': '101.0.0.2'
        },
        {
            'amount': 8900, 'frequency': 5, 'deviation': 0.25, 'days_since': 2, 'hour': 11,
            'day': 4, 'month': 3, 'trans_type': 'Subscription', 'gateway': 'UPI Pay',
            'device': 'Windows', 'merchant': 'Other', 'channel': 'Online',
            'state': 'Karnataka', 'city': 'Bangalore', 'ip': '101.0.0.3'
        },
        {
            'amount': 156000, 'frequency': 25, 'deviation': 0.92, 'days_since': 90, 'hour': 3,
            'day': 5, 'month': 3, 'trans_type': 'Investment', 'gateway': 'Dummy Bank',
            'device': 'Unknown', 'merchant': 'Investment', 'channel': 'Online',
            'state': 'Other', 'city': 'Other', 'ip': '185.0.0.1'
        },
        {
            'amount': 3500, 'frequency': 2, 'deviation': 0.08, 'days_since': 0, 'hour': 9,
            'day': 5, 'month': 3, 'trans_type': 'Purchase', 'gateway': 'UPI Pay',
            'device': 'Android', 'merchant': 'Home delivery', 'channel': 'Mobile',
            'state': 'Tamil Nadu', 'city': 'Chennai', 'ip': '101.0.0.5'
        },
        {
            'amount': 75000, 'frequency': 15, 'deviation': 0.78, 'days_since': 45, 'hour': 23,
            'day': 6, 'month': 3, 'trans_type': 'Investment', 'gateway': 'Gamma Bank',
            'device': 'MacOS', 'merchant': 'Financial services and Taxes', 'channel': 'Online',
            'state': 'Gujarat', 'city': 'Ahmedabad', 'ip': '101.0.0.6'
        },
        {
            'amount': 2300, 'frequency': 1, 'deviation': 0.02, 'days_since': 1, 'hour': 8,
            'day': 6, 'month': 3, 'trans_type': 'Refund', 'gateway': 'UPI Pay',
            'device': 'iOS', 'merchant': 'Purchases', 'channel': 'Mobile',
            'state': 'West Bengal', 'city': 'Kolkata', 'ip': '101.0.0.7'
        },
        {
            'amount': 42000, 'frequency': 12, 'deviation': 0.65, 'days_since': 20, 'hour': 16,
            'day': 7, 'month': 3, 'trans_type': 'Bill Payment', 'gateway': 'CReditPAY',
            'device': 'Windows', 'merchant': 'Financial services and Taxes', 'channel': 'Online',
            'state': 'Rajasthan', 'city': 'Jaipur', 'ip': '101.0.0.8'
        },
        {
            'amount': 180000, 'frequency': 30, 'deviation': 0.95, 'days_since': 180, 'hour': 4,
            'day': 7, 'month': 3, 'trans_type': 'Investment', 'gateway': 'Dummy Bank',
            'device': 'Unknown', 'merchant': 'Other', 'channel': 'Online',
            'state': 'Other', 'city': 'Other', 'ip': '185.0.0.2'
        },
        {
            'amount': 1500, 'frequency': 4, 'deviation': 0.12, 'days_since': 0, 'hour': 12,
            'day': 8, 'month': 3, 'trans_type': 'Purchase', 'gateway': 'SamplePay',
            'device': 'Android', 'merchant': 'Travel bookings', 'channel': 'Mobile',
            'state': 'Punjab', 'city': 'Pune', 'ip': '101.0.0.10'
        }
    ]

# UI option lists (kept in sync with the original dataset encoding)
UI_CONFIG = {
    'transaction_types': [
        "Bill Payment",
        "Investment",
        "Other",
        "Purchase",
        "Refund",
        "Subscription",
    ],
    'gateways': [
        "Bank of Data",
        "CReditPAY",
        "Dummy Bank",
        "Gamma Bank",
        "Other",
        "SamplePay",
        "Sigma Bank",
        "UPI Pay",
    ],
    'devices': ["MacOS", "Windows", "iOS", "Android"],
    'merchants': [
        "Donations and Devotion",
        "Financial services and Taxes",
        "Home delivery",
        "Investment",
        "More Services",
        "Other",
        "Purchases",
        "Travel bookings",
        "Utilities",
    ],
    'states': ['Maharashtra', 'Karnataka', 'Delhi', 'Tamil Nadu', 'Gujarat', 'Rajasthan', 'Punjab', 'Haryana', 'Uttar Pradesh', 'West Bengal'],
    'cities': ['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Ahmedabad', 'Jaipur', 'Pune', 'Kolkata', 'Hyderabad', 'Surat'],
}

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _predict(data: dict, explain: bool = False):
    """Enhanced ensemble fraud detection using ML model, rules, and AI analysis"""
    predictions = []
    probabilities = []
    reasons = []
    confidence_scores = []

    # 1. ML Model Prediction (if available)
    ml_prediction = None
    ml_proba = None
    if model is not None:
        try:
            features = _extract_ml_features(data)
            expected_features = len(features)
            
            # Check if feature count matches
            if all_features is None or (isinstance(all_features, (int, list)) and len(features) == (all_features if isinstance(all_features, int) else len(all_features))):
                ml_proba = model.predict_proba([features])[0]  # [not_fraud, fraud]
                ml_prediction = 1 if ml_proba[1] > 0.5 else 0
                predictions.append(ml_prediction)
                probabilities.append(ml_proba)
                confidence_scores.append(max(ml_proba))
                reasons.append("ML Model Analysis")
                print(f"[ML] Prediction: {ml_prediction}, Proba: {ml_proba}")
            else:
                print(f"[ML] Feature mismatch: got {len(features)}, expected {all_features}")
        except Exception as e:
            print(f"[ML] Error: {e}")

    # 2. Advanced Rule-Based Prediction
    rule_pred, rule_proba, rule_reasons = _advanced_rule_based_prediction(data)
    predictions.append(rule_pred)
    probabilities.append(rule_proba)
    confidence_scores.append(max(rule_proba))
    reasons.append("Rule-Based Analysis")
    print(f"[RULES] Prediction: {rule_pred}, Proba: {rule_proba}, Reasons: {rule_reasons}")

    # 3. AI Zero-Shot Classification (with enhanced description)
    ai_prediction = None
    ai_proba = None
    if HF_TOKEN:
        try:
            text = _create_enhanced_description(data)
            headers = {"Authorization": f"Bearer {HF_TOKEN}"}
            payload = {
                "inputs": text,
                "parameters": {"candidate_labels": ["fraudulent", "legitimate"]}
            }

            response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()

            labels = result[0]['labels']
            scores = result[0]['scores']

            if labels[0] == "fraudulent":
                ai_proba = [scores[1], scores[0]]  # [not_fraud, fraud]
            else:
                ai_proba = [scores[0], scores[1]]  # [not_fraud, fraud]

            ai_prediction = 1 if ai_proba[1] > 0.5 else 0
            predictions.append(ai_prediction)
            probabilities.append(ai_proba)
            confidence_scores.append(max(ai_proba))
            reasons.append("AI Analysis")
            print(f"[AI] Prediction: {ai_prediction}, Proba: {ai_proba}")
        except Exception as e:
            print(f"[AI] Error: {e}")

    # Ensemble Decision Making with Improved Consistency
    if not predictions:
        # Fallback if all methods fail
        final_prediction = 1 if float(data.get('amount', 0)) > 50000 else 0
        final_proba = [0.1, 0.9] if final_prediction == 1 else [0.9, 0.1]
        uncertainty = 0.8  # High uncertainty for fallback
        print("[ENSEMBLE] Using fallback prediction")
    else:
        # Dynamic weighting based on prediction confidence and method reliability
        weights = []
        confidences = []

        for i, reason in enumerate(reasons):
            conf_score = confidence_scores[i]
            confidences.append(conf_score)

            # Base weights with confidence adjustment
            if reason == "ML Model Analysis":
                base_weight = 0.5
            elif reason == "Rule-Based Analysis":
                base_weight = 0.3
            elif reason == "AI Analysis":
                base_weight = 0.2
            else:
                base_weight = 0.1

            # Adjust weight based on confidence (higher confidence = higher weight)
            confidence_multiplier = 0.5 + (conf_score * 0.5)  # Range: 0.5 to 1.0
            adjusted_weight = base_weight * confidence_multiplier
            weights.append(adjusted_weight)

        # Calculate weighted probabilities
        total_weight = sum(weights)
        if total_weight > 0:
            weighted_fraud_prob = sum(probabilities[i][1] * weights[i] for i in range(len(probabilities))) / total_weight
            weighted_not_fraud_prob = sum(probabilities[i][0] * weights[i] for i in range(len(probabilities))) / total_weight

            # Normalize to ensure they sum to 1
            total_prob = weighted_fraud_prob + weighted_not_fraud_prob
            if total_prob > 0:
                weighted_fraud_prob /= total_prob
                weighted_not_fraud_prob /= total_prob
        else:
            weighted_fraud_prob = 0.5
            weighted_not_fraud_prob = 0.5

        # Calculate prediction uncertainty (variance in predictions)
        fraud_predictions = [prob[1] for prob in probabilities]
        if len(fraud_predictions) > 1:
            mean_fraud = sum(fraud_predictions) / len(fraud_predictions)
            variance = sum((p - mean_fraud) ** 2 for p in fraud_predictions) / len(fraud_predictions)
            uncertainty = min(variance * 4, 1.0)  # Scale variance to 0-1 range
        else:
            # For single method, estimate uncertainty based on confidence distance from 0.5
            conf_from_threshold = abs(fraud_predictions[0] - 0.5)
            uncertainty = max(0.1, 1.0 - (conf_from_threshold * 2))  # Higher uncertainty when closer to 0.5

        # Apply decision threshold with uncertainty adjustment
        # More uncertain predictions require higher confidence to be classified as fraud
        fraud_threshold = 0.5 + (uncertainty * 0.2)  # Range: 0.5 to 0.7

        final_prediction = 1 if weighted_fraud_prob > fraud_threshold else 0
        final_proba = [weighted_not_fraud_prob, weighted_fraud_prob]

        print(f"[ENSEMBLE] Weighted proba: {final_proba}, Threshold: {fraud_threshold:.2f}, Uncertainty: {uncertainty:.2f}")

        # Consistency check: Compare with historical patterns
        if len(transaction_history) >= 10:
            recent_predictions = transaction_history[-10:]
            avg_historical_fraud_rate = sum(1 for t in recent_predictions if t['result']['fraud']) / len(recent_predictions)

            # Adjust prediction if it deviates significantly from historical patterns
            if abs(weighted_fraud_prob - avg_historical_fraud_rate) > 0.3:
                # Blend with historical average for more consistency
                blend_factor = 0.2  # 20% historical influence
                blended_fraud_prob = (weighted_fraud_prob * (1 - blend_factor)) + (avg_historical_fraud_rate * blend_factor)
                final_prediction = 1 if blended_fraud_prob > fraud_threshold else 0
                final_proba = [1 - blended_fraud_prob, blended_fraud_prob]
                print(f"[CONSISTENCY] Adjusted prediction using historical patterns: {final_proba}")

    # Fetch location from IP
    ip = data.get('ip', '8.8.8.8')
    location = {'country': 'Unknown', 'city': 'Unknown', 'lat': 20, 'lon': 78}
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        if response.ok:
            loc_data = response.json()
            location = {
                'country': loc_data.get('country', 'Unknown'),
                'city': loc_data.get('city', 'Unknown'),
                'lat': loc_data.get('lat', 20),
                'lon': loc_data.get('lon', 78)
            }
    except Exception as e:
        print(f"[LOCATION] Error: {e}")

    # Location-based risk adjustment
    risk_boost = 0
    high_risk_countries = ['Nigeria', 'Russia', 'China', 'Ukraine', 'Brazil']
    if location['country'] in high_risk_countries:
        risk_boost = 0.15  # Increase fraud probability by 15%

    # Additional location risk based on distance from user's typical location
    # (This would require storing user location history - simplified for now)

    adjusted_proba_fraud = min(final_proba[1] + risk_boost, 1.0)
    adjusted_proba_not_fraud = 1.0 - adjusted_proba_fraud
    final_prediction = 1 if adjusted_proba_fraud > 0.5 else 0

    # Compile all reasons from different methods
    all_reasons = []
    if "Rule-Based Analysis" in reasons:
        rule_idx = reasons.index("Rule-Based Analysis")
        if rule_pred == 1:
            all_reasons.extend(rule_reasons)

    # Create comprehensive result with uncertainty quantification
    # Calibrate confidence based on uncertainty
    calibrated_confidence = final_proba[1] if final_prediction == 1 else final_proba[0]
    # Reduce confidence based on uncertainty
    calibrated_confidence = calibrated_confidence * (1 - uncertainty * 0.3)  # Reduce by up to 30% based on uncertainty

    # Calculate reliability score (0-100) based on method agreement and confidence
    method_agreement = 1.0 - uncertainty  # Higher agreement = higher reliability
    reliability_score = int((method_agreement * calibrated_confidence) * 100)

    result = {
        'fraud': bool(final_prediction == 1),
        'label': 'Fraud' if final_prediction == 1 else 'Not Fraud',
        'confidence': round(float(calibrated_confidence) * 100, 1),
        'reliability_score': reliability_score,
        'uncertainty': round(float(uncertainty) * 100, 1),
        'proba_not_fraud': round(float(final_proba[0]) * 100, 1),
        'proba_fraud': round(float(final_proba[1]) * 100, 1),
        'location': location,
        'timestamp': datetime.now().isoformat(),
        'methods_used': reasons,
        'method_confidences': [round(c * 100, 1) for c in confidence_scores],
        'risk_factors': all_reasons[:5],  # Top 5 risk factors
        'summary': (
            f"Amount: ₹{data.get('amount')}\n"
            f"Frequency: {data.get('frequency')}\n"
            f"Deviation: {data.get('deviation')}\n"
            f"Days since: {data.get('days_since')}\n"
            f"Hour: {data.get('hour')}\n"
            f"Day: {data.get('day')}\n"
            f"Month: {data.get('month')}\n"
            f"Type: {data.get('trans_type')}\n"
            f"Gateway: {data.get('gateway')}\n"
            f"Device: {data.get('device')}\n"
            f"Merchant: {data.get('merchant')}\n"
            f"Channel: {data.get('channel')}\n"
            f"Location: {location['city']}, {location['country']}\n"
            f"Risk Factors: {', '.join(all_reasons[:3])}\n"
            f"Reliability: {reliability_score}%, Uncertainty: {round(uncertainty * 100, 1)}%"
        ),
    }

    # Save to history
    history_entry = {
        'id': len(transaction_history) + 1,
        'data': data.copy(),
        'result': result.copy(),
        'timestamp': result['timestamp']
    }
    transaction_history.append(history_entry)
    if len(transaction_history) > MAX_HISTORY:
        transaction_history.pop(0)

    # Send alerts for high-risk transactions
    if result['fraud'] and result['confidence'] > 70:
        print(f"[ALERT] High-risk transaction detected! Sending alerts...")
        
        # Send email alert
        if EMAIL_ENABLED:
            _send_email_alert(data, result)
        
        # Send SMS alert
        if SMS_ENABLED:
            _send_sms_alert(data, result)
        
        # Emit real-time alert via WebSocket
        socketio.emit('high_risk_alert', {
            'message': f'High fraud risk detected: ₹{data.get("amount", 0)}',
            'confidence': result['confidence'],
            'location': result['location'],
            'timestamp': result['timestamp']
        })

    # Enhanced AI explanation
    if explain:
        try:
            explanation_prompt = (
                f"Explain why this transaction was predicted as {result['label']} "
                f"with {result['confidence']}% confidence. Key factors: {', '.join(all_reasons[:3])}. "
                f"Transaction details: ₹{data.get('amount')} {data.get('trans_type')} via {data.get('gateway')} "
                f"on {data.get('device')} device. Keep explanation concise and focus on risk signals."
            )

            response = requests.post(
                'https://api-inference.huggingface.co/models/gpt2',
                json={'inputs': explanation_prompt, 'parameters': {'max_length': 150, 'temperature': 0.7}},
                timeout=10
            )
            if response.ok:
                generated = response.json()[0]['generated_text']
                clean_explanation = generated.replace(explanation_prompt, '').strip()
                result['ai_explanation'] = clean_explanation[:250] if clean_explanation else "Analysis complete."
            else:
                result['ai_explanation'] = f"Transaction flagged as {result['label']} due to: {', '.join(all_reasons[:2])}"
        except Exception as e:
            print(f"[EXPLANATION] Error: {e}")
            result['ai_explanation'] = f"Transaction flagged as {result['label']} due to: {', '.join(all_reasons[:2])}"

    return result


# -----------------------------------------------------------------------------
# Flask app
# -----------------------------------------------------------------------------

app = Flask(__name__, static_folder='static', template_folder='templates')
socketio = SocketIO(app, cors_allowed_origins="*")


@socketio.on('simulate_transaction')
def simulate_transaction():
    # Generate fake transaction data
    fake_data = {
        'amount': round(random.uniform(10, 1000), 2),
        'frequency': random.randint(1, 10),
        'deviation': round(random.uniform(0, 50), 2),
        'days_since': random.randint(0, 30),
        'hour': random.randint(0, 23),
        'day': random.randint(0, 6),
        'month': random.randint(1, 12),
        'trans_type': random.choice(UI_CONFIG['transaction_types']),
        'gateway': random.choice(UI_CONFIG['gateways']),
        'device': random.choice(UI_CONFIG['devices']),
        'merchant': random.choice(UI_CONFIG['merchants']),
        'channel': random.choice(['Mobile', 'Online']),
        'state': random.choice(UI_CONFIG['states']) if UI_CONFIG['states'] else '',
        'city': random.choice(UI_CONFIG['cities']) if UI_CONFIG['cities'] else '',
        'ip': f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",  # Fake IP
    }
    result = _predict(fake_data)
    emit('new_transaction', {'data': fake_data, 'result': result})


@app.route('/')
def index():
    return render_template(
        'index.html',
        config=UI_CONFIG,
        openai_enabled=OPENAI_AVAILABLE and bool(os.getenv('OPENAI_API_KEY')),
    )


@app.route('/api/predict', methods=['POST'])
def predict_api():
    payload = request.get_json(force=True, silent=True) or {}
    explain = bool(payload.get('explain', False))

    result = _predict(payload, explain=explain)
    return jsonify(result)


@app.route('/api/history', methods=['GET'])
def get_history():
    """Get transaction history."""
    limit = request.args.get('limit', 20, type=int)
    return jsonify({
        'history': transaction_history[-limit:],
        'total': len(transaction_history)
    })


@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """Get analytics statistics."""
    if not transaction_history:
        return jsonify({
            'total_transactions': 0,
            'fraud_count': 0,
            'not_fraud_count': 0,
            'fraud_rate': 0,
            'avg_fraud_probability': 0,
            'high_risk_count': 0,
            'recent_trends': [],
            'risk_by_hour': {},
            'risk_by_amount_range': {}
        })
    
    fraud_count = sum(1 for t in transaction_history if t['result']['fraud'])
    not_fraud_count = len(transaction_history) - fraud_count
    
    # Calculate average fraud probability
    fraud_probs = [t['result']['proba_fraud'] for t in transaction_history]
    avg_fraud_prob = sum(fraud_probs) / len(fraud_probs) if fraud_probs else 0
    
    # High risk (confidence > 70%)
    high_risk = sum(1 for t in transaction_history if t['result']['fraud'] and t['result']['confidence'] > 70)
    
    # Risk by hour
    risk_by_hour = {}
    for t in transaction_history:
        hour = t['data'].get('hour', 0)
        if hour not in risk_by_hour:
            risk_by_hour[hour] = {'total': 0, 'fraud': 0}
        risk_by_hour[hour]['total'] += 1
        if t['result']['fraud']:
            risk_by_hour[hour]['fraud'] += 1
    
    # Risk by amount range
    amount_ranges = {
        '0-500': {'total': 0, 'fraud': 0},
        '500-2000': {'total': 0, 'fraud': 0},
        '2000-5000': {'total': 0, 'fraud': 0},
        '5000+': {'total': 0, 'fraud': 0}
    }
    for t in transaction_history:
        amount = t['data'].get('amount', 0)
        if amount < 500:
            key = '0-500'
        elif amount < 2000:
            key = '500-2000'
        elif amount < 5000:
            key = '2000-5000'
        else:
            key = '5000+'
        amount_ranges[key]['total'] += 1
        if t['result']['fraud']:
            amount_ranges[key]['fraud'] += 1
    
    # Recent trends (last 10 transactions)
    recent = transaction_history[-10:]
    recent_trends = [
        {
            'id': t['id'],
            'amount': t['data'].get('amount'),
            'fraud': t['result']['fraud'],
            'confidence': t['result']['confidence'],
            'timestamp': t['timestamp']
        }
        for t in recent
    ]
    
    return jsonify({
        'total_transactions': len(transaction_history),
        'fraud_count': fraud_count,
        'not_fraud_count': not_fraud_count,
        'fraud_rate': round(fraud_count / len(transaction_history) * 100, 2) if transaction_history else 0,
        'avg_fraud_probability': round(avg_fraud_prob, 2),
        'high_risk_count': high_risk,
        'recent_trends': recent_trends,
        'risk_by_hour': risk_by_hour,
        'risk_by_amount_range': amount_ranges
    })


@app.route('/api/model-info', methods=['GET'])
def get_model_info():
    """Get model information."""
    model_type = "Hugging Face Zero-Shot Classification (facebook/bart-large-mnli)"
    
    # No feature importances for API-based model
    feature_importance = {}
    
    return jsonify({
        'model_type': model_type,
        'num_features': "Text-based (tabular data converted to natural language)",
        'feature_names': ["Converted to descriptive text for AI analysis"],
        'feature_importance': feature_importance,
        'training_info': 'Zero-shot on general knowledge, adapted for financial fraud',
        'version': '1.0.0'
    })


@app.route('/api/batch-predict', methods=['POST'])
def batch_predict():
    """Batch prediction endpoint for testing multiple transactions."""
    payload = request.get_json(force=True, silent=True) or {}
    transactions = payload.get('transactions', [])
    
    if not transactions:
        return jsonify({'error': 'No transactions provided'}), 400
    
    if len(transactions) > 50:
        return jsonify({'error': 'Maximum 50 transactions allowed per batch'}), 400
    
    results = []
    for i, trans in enumerate(transactions):
        try:
            result = _predict(trans, explain=False)
            results.append({
                'index': i,
                'success': True,
                'result': result
            })
        except Exception as e:
            results.append({
                'index': i,
                'success': False,
                'error': str(e)
            })
    
    return jsonify({
        'total': len(transactions),
        'results': results,
        'summary': {
            'fraud_count': sum(1 for r in results if r.get('success') and r['result']['fraud']),
            'not_fraud_count': sum(1 for r in results if r.get('success') and not r['result']['fraud']),
            'error_count': sum(1 for r in results if not r.get('success'))
        }
    })


@app.route('/api/export', methods=['GET'])
def export_history():
    """Export transaction history as CSV."""
    if not transaction_history:
        return jsonify({'error': 'No history to export'}), 400
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'ID', 'Timestamp', 'Amount', 'Transaction Type', 'Payment Gateway',
        'Device', 'Merchant', 'State', 'City', 'Channel', 'Frequency',
        'Deviation', 'Days Since', 'Hour', 'Day', 'Month',
        'Prediction', 'Confidence', 'Fraud Probability', 'Location'
    ])
    
    # Data
    for t in transaction_history:
        writer.writerow([
            t['id'],
            t['timestamp'],
            t['data'].get('amount'),
            t['data'].get('trans_type'),
            t['data'].get('gateway'),
            t['data'].get('device'),
            t['data'].get('merchant'),
            t['data'].get('state'),
            t['data'].get('city'),
            t['data'].get('channel'),
            t['data'].get('frequency'),
            t['data'].get('deviation'),
            t['data'].get('days_since'),
            t['data'].get('hour'),
            t['data'].get('day'),
            t['data'].get('month'),
            t['result']['label'],
            t['result']['confidence'],
            t['result']['proba_fraud'],
            f"{t['result']['location']['city']}, {t['result']['location']['country']}"
        ])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'fraud_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        user_lower = user_message.lower()
        
        # Get recent transaction data for context
        recent_stats = {}
        if transaction_history:
            fraud_count = sum(1 for t in transaction_history if t['result']['fraud'])
            recent_stats = {
                'total': len(transaction_history),
                'fraud': fraud_count,
                'rate': round(fraud_count / len(transaction_history) * 100, 1) if transaction_history else 0
            }
        
        # Comprehensive finance/fraud assistant responses
        if any(word in user_lower for word in ['hello', 'hi', 'hey', 'greetings']):
            bot_response = "Hello! I'm your AI Finance Assistant. I can help you with:\n• Fraud detection and transaction analysis\n• Understanding risk factors\n• Financial security tips\n• Analytics and trends\n\nWhat would you like to know?"
        
        elif any(word in user_lower for word in ['fraud', 'scam', 'fake', 'suspicious']):
            if 'detect' in user_lower or 'find' in user_lower or 'identify' in user_lower:
                bot_response = "Our fraud detection system analyzes multiple factors:\n• Transaction amount (unusually high amounts are suspicious)\n• Transaction frequency\n• Geographic location\n• Device and payment gateway\n• Time patterns (odd hours)\n• Deviation from normal behavior\n\nWould you like to analyze a specific transaction?"
            elif 'what' in user_lower and 'fraud' in user_lower:
                bot_response = "Fraud in financial transactions refers to unauthorized or deceptive transactions. Common types include:\n• Phishing scams\n• Fake payment links\n• Account takeover\n• Social engineering\n\nOur system uses AI to detect these patterns in real-time!"
            else:
                bot_response = "Fraud detection is crucial for financial security. Our AI analyzes transactions in real-time to identify suspicious patterns. Key indicators include unusual amounts, abnormal frequency, and suspicious locations. Would you like more details about how our detection works?"
        
        elif any(word in user_lower for word in ['transaction', 'payment', 'upi', 'transfer']):
            if 'history' in user_lower or 'recent' in user_lower:
                if recent_stats:
                    bot_response = f"Here are your recent transaction stats:\n• Total transactions: {recent_stats['total']}\n• Fraud detected: {recent_stats['fraud']}\n• Fraud rate: {recent_stats['rate']}%\n\nWould you like more details?"
                else:
                    bot_response = "No transactions have been analyzed yet. Would you like to submit a transaction for fraud analysis?"
            elif 'how' in user_lower and 'work' in user_lower:
                bot_response = "To analyze a transaction, fill out the form on the main page with:\n• Amount\n• Transaction type\n• Payment gateway\n• Device info\n• Location details\n\nOur AI will predict if it's fraudulent with a confidence score!"
            else:
                bot_response = "I can help you understand transactions and their risk levels. Would you like to:\n• Analyze a specific transaction\n• View transaction history\n• Learn about fraud prevention\n\nJust ask!"
        
        elif any(word in user_lower for word in ['risk', 'safe', 'security', 'protect']):
            if 'high' in user_lower or 'low' in user_lower or 'level' in user_lower:
                bot_response = "Risk levels are determined by:\n• Confidence score > 70%: High risk (red)\n• Confidence score 40-70%: Medium risk (amber)\n• Confidence score < 40%: Low risk (green)\n\nOur system flags transactions above 50% fraud probability as potentially fraudulent."
            else:
                bot_response = "To protect yourself from fraud:\n1. Never share OTP or PIN\n2. Verify payment links\n3. Check transaction alerts\n4. Use official payment apps\n5. Enable biometric locks\n\nOur AI helps detect suspicious activity automatically!"
        
        elif any(word in user_lower for word in ['analytics', 'stats', 'report', 'dashboard', 'chart']):
            if recent_stats:
                bot_response = f"Current analytics summary:\n• Total analyzed: {recent_stats['total']} transactions\n• Fraud caught: {recent_stats['fraud']}\n• Detection rate: {recent_stats['rate']}%\n\nThe dashboard shows real-time charts and trends. Check the main page for visualizations!"
            else:
                bot_response = "The analytics dashboard shows fraud trends, hourly risk patterns, and transaction distributions. Start analyzing transactions to see real-time stats!"
        
        elif any(word in user_lower for word in ['help', 'what can you do', 'capabilities']):
            bot_response = "I'm your AI Finance Assistant! I can help with:\n\n📊 Transaction Analysis - Analyze transactions for fraud risk\n\n🔍 Fraud Detection - Explain how fraud is detected\n\n📈 Analytics - View stats and trends\n\n🛡️ Security Tips - Get protection recommendations\n\n💬 General Finance - Answer finance-related questions\n\nJust type your question!"
        
        elif any(word in user_lower for word in ['thank', 'thanks', 'appreciate']):
            bot_response = "You're welcome! Feel free to ask if you have more questions about fraud detection or financial security. Stay safe!"
        
        elif any(word in user_lower for word in ['bye', 'goodbye', 'exit', 'close']):
            bot_response = "Goodbye! Remember to stay vigilant against fraud. Come back if you need any help!"
        
        elif any(word in user_lower for word in ['model', 'ai', 'machine learning', 'how do you']):
            bot_response = "Our system uses AI-powered fraud detection:\n\n• Zero-shot classification for text analysis\n• Pattern recognition across multiple features\n• Location-based risk assessment\n• Real-time transaction scoring\n\nThe model evaluates each transaction against historical patterns and anomaly detection!"
        
        elif any(word in user_lower for word in ['export', 'download', 'csv']):
            bot_response = "You can export your transaction history as CSV!\n\nClick the 'Export CSV' button in the header to download all analyzed transactions with fraud predictions and details.\n\nThis is useful for record-keeping and auditing!"
        
        elif any(word in user_lower for word in ['alert', 'notification', 'email', 'sms']):
            bot_response = "Our system supports real-time alerts!\n\n📧 Email Alerts - Get detailed HTML emails for high-risk transactions\n📱 SMS Alerts - Receive instant text messages via Twilio\n🔔 Browser Notifications - Desktop notifications for immediate awareness\n\nAlerts are triggered when fraud confidence exceeds 70%!"
        
        else:
            # Default helpful responses
            responses = [
                "I'm your AI Finance Assistant specialized in fraud detection. Ask me about:\n• Transaction analysis\n• Fraud prevention\n• Security tips\n• System analytics\n\nHow can I help?",
                "I'm not sure about that, but I can help with fraud detection, transaction analysis, or financial security. What would you like to know?",
                "That's an interesting question! I specialize in finance and fraud topics. Try asking about transactions, risk analysis, or security tips!",
                "I'd be happy to help with fraud-related questions! You can ask me about transaction analysis, risk levels, or how our detection system works."
            ]
            bot_response = random.choice(responses)
        
        return jsonify({'response': bot_response})
    
    except Exception as e:
        print(f"Chat error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/alert-config', methods=['GET', 'POST'])
def alert_config():
    """Get or update alert configuration"""
    global EMAIL_ENABLED, SMS_ENABLED, ALERT_EMAIL, ALERT_PHONE_NUMBER
    
    if request.method == 'GET':
        return jsonify({
            'email_enabled': EMAIL_ENABLED,
            'sms_enabled': SMS_ENABLED,
            'alert_email': ALERT_EMAIL,
            'alert_phone': ALERT_PHONE_NUMBER,
            'smtp_server': SMTP_SERVER,
            'smtp_port': SMTP_PORT
        })
    
    elif request.method == 'POST':
        data = request.get_json()
        
        # Update configuration (in production, save to database or config file)
        if 'email_enabled' in data:
            EMAIL_ENABLED = bool(data['email_enabled'])
        if 'sms_enabled' in data:
            SMS_ENABLED = bool(data['sms_enabled'])
        if 'alert_email' in data:
            ALERT_EMAIL = data['alert_email']
        if 'alert_phone' in data:
            ALERT_PHONE_NUMBER = data['alert_phone']
        
        return jsonify({
            'success': True,
            'message': 'Alert configuration updated successfully',
            'config': {
                'email_enabled': EMAIL_ENABLED,
                'sms_enabled': SMS_ENABLED,
                'alert_email': ALERT_EMAIL,
                'alert_phone': ALERT_PHONE_NUMBER
            }
        })


@app.route('/api/analyze-screenshot', methods=['POST'])
def analyze_screenshot_api():
    """Analyze UPI payment screenshot for authenticity and extract details"""
    if 'screenshot' not in request.files:
        return jsonify({'error': 'No screenshot provided'}), 400
    
    file = request.files['screenshot']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Validate file type
    allowed_extensions = {'png', 'jpg', 'jpeg', 'webp'}
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    
    if ext not in allowed_extensions:
        return jsonify({'error': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'}), 400
    
    try:
        # Analyze the screenshot
        result = _analyze_screenshot(file)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify({'error': result.get('message', 'Analysis failed')}), 500
            
    except Exception as e:
        print(f"[API] Screenshot analysis error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    # Add demo transactions on startup for hackathon demo
    _add_demo_transactions()
    socketio.run(app, debug=True)
