import streamlit as st
import joblib
import pandas as pd
import numpy as np

# Custom CSS for modern, creative, and colorful UI
st.markdown("""
<style>
    /* Global styles */
    body {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(45deg, #ff6b6b, #4ecdc4, #45b7d1, #f9ca24);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        animation: glow 2s ease-in-out infinite alternate;
    }
    
    @keyframes glow {
        from { text-shadow: 2px 2px 4px rgba(0,0,0,0.1); }
        to { text-shadow: 2px 2px 8px rgba(0,0,0,0.3); }
    }
    
    .sidebar-header {
        font-size: 1.8rem;
        font-weight: bold;
        background: linear-gradient(45deg, #ff9a9e, #fecfef);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    
    .result-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 2.5rem;
        border-radius: 20px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.2);
        margin-top: 2rem;
        border: 2px solid rgba(255,255,255,0.2);
        backdrop-filter: blur(10px);
        color: white;
    }
    
    .prediction-text {
        font-size: 2rem;
        font-weight: bold;
        color: #2ecc71;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .fraud-text {
        font-size: 2rem;
        font-weight: bold;
        color: #e74c3c;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .confidence-text {
        font-size: 1.5rem;
        color: #ecf0f1;
        margin-top: 1rem;
    }
    
    .input-section {
        background: rgba(255,255,255,0.1);
        padding: 1.5rem;
        border-radius: 15px;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(255,255,255,0.2);
        backdrop-filter: blur(5px);
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .section-numerical { background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); }
    .section-time { background: linear-gradient(135deg, #d299c2 0%, #fef9d7 100%); }
    .section-categorical { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    .section-location { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
    
    /* Button styling */
    .stButton>button {
        background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 12px 30px;
        font-size: 1.2rem;
        font-weight: bold;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
    }
    
    /* Input styling */
    .stNumberInput input, .stSelectbox select, .stRadio div {
        background: rgba(255,255,255,0.9);
        border: 2px solid #ddd;
        border-radius: 10px;
        padding: 8px;
        font-size: 1rem;
    }
    
    .stSlider div {
        background: linear-gradient(45deg, #ff9a9e, #fecfef);
        border-radius: 10px;
    }
    
    /* Sidebar background */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: white;
    }
    
    /* Info box */
    .stAlert {
        background: rgba(255,255,255,0.9);
        border-radius: 10px;
        border: none;
    }
</style>
""", unsafe_allow_html=True)

# Load the model
@st.cache_resource
def load_model():
    return joblib.load('best_tuned_model.joblib')

model = load_model()

# Extract feature names from the model if available
if hasattr(model, 'feature_names_in_'):
    all_features = model.feature_names_in_
else:
    st.error("Feature names not found in model. Ensure you use the correct feature order.")
    st.stop()

# Main title
st.markdown('<div class="main-header">🔍 Transaction Analysis & Fraud Detection</div>', unsafe_allow_html=True)
st.markdown("Enter transaction details in the sidebar to analyze and predict potential fraud.")

# Sidebar for inputs
with st.sidebar:
    st.markdown('<div class="sidebar-header">📝 Transaction Details</div>', unsafe_allow_html=True)
    
    # Numerical Inputs
    with st.expander("💰 Numerical Details", expanded=True):
        st.markdown('<div class="input-section section-numerical">', unsafe_allow_html=True)
        amount = st.number_input("Transaction Amount (₹)", min_value=0.0, value=100.0, step=0.01)
        freq = st.number_input("Transaction Frequency", min_value=0, value=1)
        deviation = st.number_input("Transaction Amount Deviation", value=0.0, step=0.01)
        days_since = st.number_input("Days Since Last Transaction", min_value=0, value=0)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Time Inputs
    with st.expander("⏰ Time Details", expanded=True):
        st.markdown('<div class="input-section section-time">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            hour = st.slider("Hour of Day", 0, 23, 12)
            day = st.slider("Day of Week (0=Mon, 6=Sun)", 0, 6, 0)
        with col2:
            month = st.slider("Month (1-12)", 1, 12, 1)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Categorical Inputs
    with st.expander("🏷️ Categorical Details", expanded=True):
        st.markdown('<div class="input-section section-categorical">', unsafe_allow_html=True)
    trans_type = st.selectbox("Transaction Type", ["Bill Payment", "Investment", "Other", "Purchase", "Refund", "Subscription"])
    gateway = st.selectbox("Payment Gateway", ["Bank of Data", "CReditPAY", "Dummy Bank", "Gamma Bank", "Other", "SamplePay", "Sigma Bank", "UPI Pay"])
    device = st.selectbox("Device OS", ["MacOS", "Windows", "iOS"])
    merchant = st.selectbox("Merchant Category", ["Donations and Devotion", "Financial services and Taxes", "Home delivery", "Investment", "More Services", "Other", "Purchases", "Travel bookings", "Utilities"])
    channel = st.radio("Channel", ["Mobile", "Online"])
    
    # Location Inputs
    with st.expander("📍 Location Details", expanded=True):
        st.markdown('<div class="input-section section-location">', unsafe_allow_html=True)
    state = st.selectbox("Transaction State", [s.replace("Transaction_State_", "") for s in all_features if "Transaction_State_" in s])
    city = st.selectbox("Transaction City", [c.replace("Transaction_City_", "") for c in all_features if "Transaction_City_" in c])
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Buttons
    col1, col2 = st.columns(2)
    with col1:
        analyze_button = st.button("🔍 Analyze Transaction", type="primary", use_container_width=True)
    with col2:
        reset_button = st.button("🔄 Reset", use_container_width=True)

# Main content area
if reset_button:
    st.success("🔄 Inputs reset! Please refresh the page to clear all fields.")
    st.rerun()

if analyze_button:
    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    status_text.text("🔄 Analyzing transaction...")
    progress_bar.progress(25)
    
    # Initialize a dataframe with zeros for all model features
    input_df = pd.DataFrame(np.zeros((1, len(all_features))), columns=all_features)
    
    progress_bar.progress(50)
    status_text.text("📊 Preparing data...")
    
    # Fill Numerical values
    input_df['amount'] = amount
    input_df['Transaction_Frequency'] = freq
    input_df['Transaction_Amount_Deviation'] = deviation
    input_df['Days_Since_Last_Transaction'] = days_since
    input_df['Hour'] = hour
    input_df['Day_of_Week'] = day
    input_df['Month'] = month
    
    # Fill One-Hot Encoded values
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
    
    progress_bar.progress(75)
    status_text.text("🤖 Running prediction...")
    
    # Prediction
    prediction = model.predict(input_df)
    proba = model.predict_proba(input_df)
    
    progress_bar.progress(100)
    status_text.text("✅ Analysis complete!")
    
    # Clear progress
    progress_bar.empty()
    status_text.empty()
    
    # Display results in a modern card
    st.markdown('<div class="result-card">', unsafe_allow_html=True)
    st.subheader("📊 Analysis Result")
    
    class_label = "Fraud" if prediction[0] == 1 else "Not Fraud"
    color_class = "fraud-text" if prediction[0] == 1 else "prediction-text"
    
    st.markdown(f'<div class="{color_class}">Predicted: {class_label}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="confidence-text">Confidence: {max(proba[0])*100:.2f}%</div>', unsafe_allow_html=True)
    
    # Confidence meter
    st.progress(max(proba[0]))
    
    # Additional insights
    if prediction[0] == 1:
        st.error("⚠️ This transaction has been flagged as potentially fraudulent. Please review carefully.")
        st.balloons()  # Fun animation for fraud detection
    else:
        st.success("✅ This transaction appears legitimate.")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Additional interactive elements
    with st.expander("📈 Detailed Probabilities"):
        st.write("**Prediction Probabilities:**")
        prob_df = pd.DataFrame({
            'Class': ['Not Fraud', 'Fraud'],
            'Probability': [f"{proba[0][0]*100:.2f}%", f"{proba[0][1]*100:.2f}%"]
        })
        st.table(prob_df)
        
        # Simple bar chart
        st.bar_chart(prob_df.set_index('Class')['Probability'].str.rstrip('%').astype(float))
else:
    # Placeholder when no analysis is done
    st.info("👈 Enter details in the sidebar and click 'Analyze Transaction' to get started.")
    
    # Fun welcome animation
    if st.button("🎉 Show Welcome Animation"):
        st.balloons()
        st.snow()