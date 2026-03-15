# 🛡️ UPI Fraud Detector | Hackathon Edition

A cutting-edge web application for real-time UPI transaction fraud detection, built for 24-hour hackathons. Features AI-powered predictions, live simulation, advanced analytics, and a modern dashboard.

## 🚀 Key Features

### Core Features
- **Real-Time Fraud Detection**: Machine learning model predicts fraud risk instantly
- **Live Transaction Simulation**: Continuous fake transaction generation via WebSocket
- **AI Explanations**: Free Hugging Face integration for prediction insights
- **Batch Prediction**: Test multiple transactions at once

### Dashboard & Analytics
- **📊 Live Stats Dashboard**: Total transactions, fraud count, fraud rate, high-risk alerts
- **📈 Interactive Charts**: Doughnut chart for fraud distribution, bar chart for hourly risk analysis
- **🗺️ Geographic Mapping**: Interactive map showing transaction locations
- **📋 Transaction History**: Recent transactions table with filtering
- **📥 CSV Export**: Download all transaction history

### UI/UX Enhancements
- **🌙 Dark/Light Mode**: User-friendly theme toggle with persistence
- **🔔 Browser Notifications**: Real-time alerts for high-risk transactions
- **📱 Responsive Design**: Works on mobile, tablet, and desktop
- **✨ Modern Glassmorphism**: Beautiful translucent cards with blur effects
- **🎯 Risk Meter**: Visual gradient showing fraud probability
- **ℹ️ Model Info Panel**: View model type, features, and feature importance

## 🎯 Hackathon Impact

| Category | Description |
|----------|-------------|
| **Innovation** | Combines ML, real-time data, AI explanations, and analytics |
| **Tech Depth** | Flask-SocketIO, Chart.js, Leaflet Maps, ML model insights |
| **User Experience** | Modern UI, animations, responsive design, notifications |
| **Demo-Ready** | Instant predictions, live simulation, export functionality |
| **Scalability** | Can handle multiple users, deployable to cloud |

## 🛠️ Tech Stack

- **Backend**: Flask + Flask-SocketIO (Python)
- **Frontend**: Tailwind CSS + Chart.js + Leaflet Maps + Vanilla JS
- **ML**: scikit-learn (DecisionTreeClassifier)
- **AI**: Hugging Face GPT-2 (free API)
- **Deployment**: Railway/Render (free tier)

## 📦 Quick Start

```bash
# 1. Clone and setup virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate  # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the application
python app.py

# 4. Open in browser
http://127.0.0.1:5000
```

## 🎬 Demo Script (5 Minutes)

1. **Theme Toggle**: Click the theme button to switch between dark/light modes
2. **Enter Transaction**: Fill in the form with transaction details
3. **Analyze**: Click "Analyze Transaction" to see prediction
4. **View Results**: See fraud prediction, confidence, risk meter, and location
5. **AI Explanation**: Check "Generate AI explanation" for additional insights
6. **Start Simulation**: Click "Start Simulation" to see live transactions every 3 seconds
7. **View Dashboard**: Watch stats update in real-time
8. **Check History**: View recent transactions table
9. **Export**: Click "Export CSV" to download transaction history
10. **Model Info**: Click "Model Info" to see feature importance

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/predict` | POST | Predict fraud for a single transaction |
| `/api/batch-predict` | POST | Predict fraud for multiple transactions |
| `/api/history` | GET | Get transaction history |
| `/api/analytics` | GET | Get analytics statistics |
| `/api/model-info` | GET | Get model information and feature importance |
| `/api/export` | GET | Export history as CSV |

## 🏆 Why This Wins Hackathons

1. **Problem Solved**: UPI fraud is rising; this provides instant, AI-backed detection
2. **Tech Stack**: Modern, relevant technologies that judges recognize
3. **Polish**: Beautiful UI with glassmorphism, animations, and smooth interactions
4. **Features**: Complete package - predictions, analytics, visualization, export
5. **Demo Effect**: Live simulation creates immediate visual impact

## 📁 Project Structure

```
fraud_detector/
├── app.py              # Flask application with all API endpoints
├── requirements.txt    # Python dependencies
├── static/
│   ├── css/style.css   # Custom styles
│   ├── js/app.js       # Frontend JavaScript
│   └── manifest.json   # PWA manifest
└── templates/
    └── index.html      # Main HTML template
```

## 🔧 Configuration

The application uses environment variables:
- `OPENAI_API_KEY`: Enable AI explanations (optional)

## 📝 License

MIT License - Built for [Hackathon Name]! 🚀

