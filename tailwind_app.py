from flask import Flask, render_template_string, request
import joblib
import pandas as pd
import numpy as np
import os

# Optional AI integration via OpenAI
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

app = Flask(__name__)

# Load model once
model = joblib.load('best_tuned_model.joblib')
all_features = model.feature_names_in_

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>UPI Fraud Detection</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gradient-to-br from-slate-900 via-indigo-900 to-slate-900 text-white min-h-screen">
  <div class="max-w-5xl mx-auto px-4 py-12">
    <header class="text-center mb-10">
      <h1 class="text-4xl font-extrabold tracking-tight">UPI Fraud Detection</h1>
      <p class="mt-3 text-slate-200">Enter transaction details to see fraud probability.</p>
    </header>

    <div class="grid lg:grid-cols-2 gap-8">
      <form method="post" class="space-y-6 bg-white/10 backdrop-blur rounded-2xl p-8 shadow-lg border border-white/10">
        <h2 class="text-xl font-semibold text-white">Transaction Details</h2>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <label class="block">
            <span class="text-sm text-slate-200">Amount (₹)</span>
            <input name="amount" type="number" step="0.01" value="100.00" class="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white" required />
          </label>
          <label class="block">
            <span class="text-sm text-slate-200">Frequency</span>
            <input name="frequency" type="number" value="1" min="0" class="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white" required />
          </label>
          <label class="block">
            <span class="text-sm text-slate-200">Amount Deviation</span>
            <input name="deviation" type="number" step="0.01" value="0.00" class="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white" required />
          </label>
          <label class="block">
            <span class="text-sm text-slate-200">Days Since Last</span>
            <input name="days_since" type="number" value="0" min="0" class="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white" required />
          </label>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <label class="block">
            <span class="text-sm text-slate-200">Hour</span>
            <input name="hour" type="number" min="0" max="23" value="12" class="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white" required />
          </label>
          <label class="block">
            <span class="text-sm text-slate-200">Day of Week (0=Mon)</span>
            <input name="day" type="number" min="0" max="6" value="0" class="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white" required />
          </label>
          <label class="block">
            <span class="text-sm text-slate-200">Month (1-12)</span>
            <input name="month" type="number" min="1" max="12" value="1" class="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white" required />
          </label>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <label class="block">
            <span class="text-sm text-slate-200">Transaction Type</span>
            <select name="trans_type" class="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white">
              {% for t in transaction_types %}
              <option value="{{t}}">{{t}}</option>
              {% endfor %}
            </select>
          </label>

          <label class="block">
            <span class="text-sm text-slate-200">Payment Gateway</span>
            <select name="gateway" class="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white">
              {% for g in gateways %}
              <option value="{{g}}">{{g}}</option>
              {% endfor %}
            </select>
          </label>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <label class="block">
            <span class="text-sm text-slate-200">Device OS</span>
            <select name="device" class="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white">
              {% for d in devices %}
              <option value="{{d}}">{{d}}</option>
              {% endfor %}
            </select>
          </label>
          <label class="block">
            <span class="text-sm text-slate-200">Merchant Category</span>
            <select name="merchant" class="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white">
              {% for m in merchants %}
              <option value="{{m}}">{{m}}</option>
              {% endfor %}
            </select>
          </label>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <label class="block">
            <span class="text-sm text-slate-200">Channel</span>
            <select name="channel" class="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white">
              <option value="Mobile">Mobile</option>
              <option value="Online">Online</option>
            </select>
          </label>
          <label class="block">
            <span class="text-sm text-slate-200">State</span>
            <select name="state" class="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white">
              {% for s in states %}
              <option value="{{s}}">{{s}}</option>
              {% endfor %}
            </select>
          </label>
        </div>

        <label class="block">
          <span class="text-sm text-slate-200">City</span>
          <select name="city" class="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white">
            {% for c in cities %}
            <option value="{{c}}">{{c}}</option>
            {% endfor %}
          </select>
        </label>

        <div class="flex items-center justify-between gap-3">
          <label class="flex items-center gap-2 text-sm text-slate-200">
            <input type="checkbox" name="explain" value="yes" class="h-4 w-4 rounded border border-slate-700 bg-slate-950 text-indigo-500" {% if not openai_enabled %}disabled{% endif %}>
            Generate AI explanation
          </label>
          {% if not openai_enabled %}
          <span class="text-xs text-slate-400">Enable by setting OPENAI_API_KEY.</span>
          {% endif %}
        </div>

        <button type="submit" class="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-500 to-cyan-500 font-semibold text-white shadow-lg hover:from-indigo-600 hover:to-cyan-600 transition">Analyze</button>
      </form>

      <div class="bg-white/10 backdrop-blur rounded-2xl p-8 shadow-lg border border-white/10">
        <h2 class="text-xl font-semibold mb-4">Result</h2>
        {% if result %}
        <div class="space-y-4">
          <div class="rounded-xl p-4 bg-white/10 border border-white/15">
            <p class="text-sm text-slate-200">Predicted</p>
            <p class="text-2xl font-semibold {{ 'text-emerald-300' if not result.fraud else 'text-rose-300' }}">{{ result.label }}</p>
            <p class="text-sm text-slate-300">Confidence: {{ result.confidence }}%</p>
          </div>
          <div class="rounded-xl p-4 bg-white/10 border border-white/15">
            <p class="text-sm text-slate-200">Probabilities</p>
            <ul class="mt-2 text-sm text-slate-200 space-y-1">
              <li>Not Fraud: {{ result.proba_not_fraud }}%</li>
              <li>Fraud: {{ result.proba_fraud }}%</li>
            </ul>
          </div>
          <div class="rounded-xl p-4 bg-white/10 border border-white/15">
            <p class="text-sm text-slate-200">Input summary</p>
            <pre class="mt-2 text-xs text-slate-200 whitespace-pre-wrap">{{ result.summary }}</pre>
          </div>
          {% if ai_explanation %}
          <div class="rounded-xl p-4 bg-white/10 border border-white/15">
            <p class="text-sm text-slate-200">AI explanation</p>
            <pre class="mt-2 text-xs text-slate-200 whitespace-pre-wrap">{{ ai_explanation }}</pre>
          </div>
          {% endif %}
        </div>
        {% else %}
        <p class="text-slate-300">Fill in the form and click Analyze to see the prediction.</p>
        {% endif %}
      </div>
    </div>

    <footer class="mt-12 text-center text-sm text-slate-400">Powered by Tailwind CSS • Model: DecisionTreeClassifier</footer>
  </div>
</body>
</html>
"""


@app.route('/', methods=['GET', 'POST'])
def index():
    default_values = {
        'transaction_types': ["Bill Payment", "Investment", "Other", "Purchase", "Refund", "Subscription"],
        'gateways': ["Bank of Data", "CReditPAY", "Dummy Bank", "Gamma Bank", "Other", "SamplePay", "Sigma Bank", "UPI Pay"],
        'devices': ["MacOS", "Windows", "iOS"],
        'merchants': ["Donations and Devotion", "Financial services and Taxes", "Home delivery", "Investment", "More Services", "Other", "Purchases", "Travel bookings", "Utilities"],
        'states': [s.replace('Transaction_State_', '') for s in all_features if 'Transaction_State_' in s],
        'cities': [c.replace('Transaction_City_', '') for c in all_features if 'Transaction_City_' in c],
    }

    result = None
    ai_explanation = None
    if request.method == 'POST':
        data = {
            'amount': float(request.form.get('amount', 0)),
            'frequency': int(request.form.get('frequency', 0)),
            'deviation': float(request.form.get('deviation', 0)),
            'days_since': int(request.form.get('days_since', 0)),
            'hour': int(request.form.get('hour', 0)),
            'day': int(request.form.get('day', 0)),
            'month': int(request.form.get('month', 1)),
            'trans_type': request.form.get('trans_type', ''),
            'gateway': request.form.get('gateway', ''),
            'device': request.form.get('device', ''),
            'merchant': request.form.get('merchant', ''),
            'channel': request.form.get('channel', 'Mobile'),
            'state': request.form.get('state', ''),
            'city': request.form.get('city', ''),
        }
        explain = request.form.get('explain', 'no') == 'yes'

        input_df = pd.DataFrame(np.zeros((1, len(all_features))), columns=all_features)
        input_df['amount'] = data['amount']
        input_df['Transaction_Frequency'] = data['frequency']
        input_df['Transaction_Amount_Deviation'] = data['deviation']
        input_df['Days_Since_Last_Transaction'] = data['days_since']
        input_df['Hour'] = data['hour']
        input_df['Day_of_Week'] = data['day']
        input_df['Month'] = data['month']

        def set_onehot(prefix, value):
            col = f"{prefix}_{value}"
            if col in all_features:
                input_df[col] = 1

        set_onehot('Transaction_Type', data['trans_type'])
        set_onehot('Payment_Gateway', data['gateway'])
        set_onehot('Device_OS', data['device'])
        set_onehot('Merchant_Category', data['merchant'])
        set_onehot('Transaction_Channel', data['channel'])
        set_onehot('Transaction_State', data['state'])
        set_onehot('Transaction_City', data['city'])

        prediction = model.predict(input_df)[0]
        proba = model.predict_proba(input_df)[0]

        result = {
            'fraud': bool(prediction == 1),
            'label': 'Fraud' if prediction == 1 else 'Not Fraud',
            'confidence': round(max(proba) * 100, 2),
            'proba_not_fraud': round(proba[0] * 100, 2),
            'proba_fraud': round(proba[1] * 100, 2),
            'summary': (
                f"Amount: ₹{data['amount']}\n"
                f"Frequency: {data['frequency']}\n"
                f"Deviation: {data['deviation']}\n"
                f"Days since: {data['days_since']}\n"
                f"Hour: {data['hour']}\n"
                f"Day: {data['day']}\n"
                f"Month: {data['month']}\n"
                f"Type: {data['trans_type']}\n"
                f"Gateway: {data['gateway']}\n"
                f"Device: {data['device']}\n"
                f"Merchant: {data['merchant']}\n"
                f"Channel: {data['channel']}\n"
                f"Location: {data['city']}, {data['state']}"
            ),
        }

        # Optionally generate a short, model-based explanation using OpenAI.
        if explain and OPENAI_AVAILABLE and os.getenv('OPENAI_API_KEY'):
            try:
                prompt = (
                    f"Explain why a UPI transaction is predicted as {result['label']} "
                    f"given these features: {data}. "
                    "Keep the explanation concise and focus on the most influential inputs."
                )
                response = openai.Completion.create(
                    model='text-davinci-003',
                    prompt=prompt,
                    max_tokens=180,
                    temperature=0.7,
                )
                ai_explanation = response.choices[0].text.strip()
            except Exception:
                ai_explanation = "Unable to generate an explanation at this time."

    openai_enabled = OPENAI_AVAILABLE and bool(os.getenv('OPENAI_API_KEY'))

    return render_template_string(
        TEMPLATE,
        result=result,
        ai_explanation=ai_explanation,
        openai_enabled=openai_enabled,
        transaction_types=default_values['transaction_types'],
        gateways=default_values['gateways'],
        devices=default_values['devices'],
        merchants=default_values['merchants'],
        states=default_values['states'],
        cities=default_values['cities'],
    )


if __name__ == '__main__':
    app.run(debug=True)
