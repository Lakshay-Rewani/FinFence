const form = document.getElementById('transaction-form');
const resultEl = document.getElementById('result');
const submitBtn = document.getElementById('submit');

let chartData = JSON.parse(localStorage.getItem('chartData')) || { fraud: 0, notFraud: 0 };
let chart;

function formatPercent(value) {
  return `${value.toFixed(1)}%`;
}

function updateChart() {
  const ctx = document.getElementById('predictionChart').getContext('2d');
  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['Not Fraud', 'Fraud'],
      datasets: [{
        label: 'Predictions',
        data: [chartData.notFraud, chartData.fraud],
        backgroundColor: ['#10b981', '#ef4444']
      }]
    },
    options: {
      responsive: true,
      scales: {
        y: { beginAtZero: true }
      }
    }
  });
  localStorage.setItem('chartData', JSON.stringify(chartData));
}

function renderResult(data) {
  const labelColor = data.fraud ? 'text-rose-300' : 'text-emerald-300';

  if (data.fraud) chartData.fraud++; else chartData.notFraud++;
  updateChart();

  // Update map
  if (window.mapInstance && data.location.lat && data.location.lon) {
    window.mapInstance.setView([data.location.lat, data.location.lon], 10);
    L.marker([data.location.lat, data.location.lon]).addTo(window.mapInstance)
      .bindPopup(`${data.location.city}, ${data.location.country}`)
      .openPopup();
  }

  // Notification for high-risk
  if (data.fraud && data.confidence > 70) {
    if (Notification.permission === 'granted') {
      new Notification('High Fraud Risk Detected!', {
        body: `Transaction predicted as Fraud with ${data.confidence}% confidence.`,
        icon: '/static/icon-192.png'
      });
    } else if (Notification.permission !== 'denied') {
      Notification.requestPermission();
    }
  }

  const explanationBlock = data.ai_explanation
    ? `<div class="rounded-xl p-4 bg-white/10 border border-white/15">
        <p class="text-sm text-slate-200">AI explanation</p>
        <pre class="mt-2 text-xs text-slate-200 whitespace-pre-wrap">${data.ai_explanation}</pre>
      </div>`
    : '';

  resultEl.innerHTML = `
    <div class="space-y-4">
      <div class="rounded-xl p-4 bg-white/10 border border-white/15">
        <p class="text-sm text-slate-200">Predicted</p>
        <p class="text-2xl font-semibold ${labelColor}">${data.label}</p>
        <p class="text-sm text-slate-300">Confidence: ${formatPercent(data.confidence)}</p>
      </div>
      <div class="rounded-xl p-4 bg-white/10 border border-white/15">
        <p class="text-sm text-slate-200">Probabilities</p>
        <ul class="mt-2 text-sm text-slate-200 space-y-1">
          <li>Not Fraud: ${formatPercent(data.proba_not_fraud)}</li>
          <li>Fraud: ${formatPercent(data.proba_fraud)}</li>
        </ul>
      </div>
      <div class="rounded-xl p-4 bg-white/10 border border-white/15">
        <p class="text-sm text-slate-200">Location (from IP)</p>
        <p class="text-sm text-slate-200">${data.location.city}, ${data.location.country}</p>
      </div>
      <div class="rounded-xl p-4 bg-white/10 border border-white/15">
        <p class="text-sm text-slate-200">Input summary</p>
        <pre class="mt-2 text-xs text-slate-200 whitespace-pre-wrap">${data.summary}</pre>
      </div>
      ${explanationBlock}
    </div>
  `;
}

function renderLoading() {
  resultEl.innerHTML = `
    <div class="rounded-xl p-6 bg-white/10 border border-white/15 flex items-center justify-center gap-3">
      <div class="h-5 w-5 animate-spin rounded-full border-2 border-white/40 border-t-white"></div>
      <span class="text-sm text-slate-200">Analyzing transaction…</span>
    </div>
  `;
}

function renderError(message) {
  resultEl.innerHTML = `
    <div class="rounded-xl p-6 bg-rose-950/40 border border-rose-600">
      <p class="text-sm text-rose-200">${message}</p>
    </div>
  `;
}

// Fetch a random quote from a free API
async function loadQuote() {
  try {
    const response = await fetch('https://api.quotable.io/random');
    if (!response.ok) throw new Error('Failed to fetch quote');
    const data = await response.json();
    document.getElementById('quote-text').textContent = `"${data.content}"`;
    document.getElementById('quote-author').textContent = `— ${data.author}`;
  } catch (error) {
    document.getElementById('quote-text').textContent = 'Could not load a quote at this time.';
    document.getElementById('quote-author').textContent = '';
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();

  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());

  payload.amount = parseFloat(payload.amount);
  payload.frequency = parseInt(payload.frequency, 10);
  payload.deviation = parseFloat(payload.deviation);
  payload.days_since = parseInt(payload.days_since, 10);
  payload.hour = parseInt(payload.hour, 10);
  payload.day = parseInt(payload.day, 10);
  payload.month = parseInt(payload.month, 10);
  payload.explain = formData.get('explain') === 'yes';
  payload.ip = payload.ip || '8.8.8.8';  // Default IP

  submitBtn.disabled = true;
  submitBtn.textContent = 'Analyzing…';
  renderLoading();

  try {
    const response = await fetch('/api/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error('The server returned an error.');
    }

    const data = await response.json();
    renderResult(data);
  } catch (error) {
    renderError(error.message || 'Network error, please try again.');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Analyze';
  }
});

// Load quote and chart on page load
document.addEventListener('DOMContentLoaded', () => {
  console.log('DOM loaded, initializing app...');
  loadQuote();
  updateChart();

  // Initialize map
  const map = L.map('map').setView([20, 78], 4);  // India center
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
  }).addTo(map);
  window.mapInstance = map;

  // Theme toggle
  const themeToggle = document.getElementById('theme-toggle');
  const savedTheme = localStorage.getItem('theme') || 'dark';
  if (savedTheme === 'light') document.body.classList.add('light-mode');
  themeToggle.addEventListener('click', () => {
    document.body.classList.toggle('light-mode');
    const isLight = document.body.classList.contains('light-mode');
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
  });

  // Chat functionality
  const chatBtn = document.getElementById('chat-btn');
  const chatModal = document.getElementById('chat-modal');
  const closeChat = document.getElementById('close-chat');
  const chatInput = document.getElementById('chat-input');
  const sendChat = document.getElementById('send-chat');
  const voiceBtn = document.getElementById('voice-btn');
  const chatMessages = document.getElementById('chat-messages');

  console.log('Chat elements found:', {
    chatBtn: !!chatBtn,
    chatModal: !!chatModal,
    closeChat: !!closeChat,
    chatInput: !!chatInput,
    sendChat: !!sendChat,
    voiceBtn: !!voiceBtn,
    chatMessages: !!chatMessages
  });

  let recognition;
  let isListening = false;
  let isFirstMessage = true;

  chatBtn.addEventListener('click', () => {
    console.log('Chat button clicked');
    chatModal.classList.remove('hidden');
    if (isFirstMessage) {
      addMessage("Hello! I'm your AI Finance Assistant. I can help you with fraud detection, transaction analysis, security tips, and analytics. What would you like to know?", false);
      isFirstMessage = false;
    }
  });
  closeChat.addEventListener('click', () => {
    console.log('Close chat clicked');
    chatModal.classList.add('hidden');
  });

  function addMessage(text, isUser = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `p-3 rounded-lg ${isUser ? 'bg-blue-600 ml-8' : 'bg-slate-700 mr-8'}`;
    msgDiv.textContent = text;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  async function sendMessage(message) {
    console.log('Sending message:', message);
    addMessage(message, true);
    chatInput.value = '';

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
      });
      const data = await response.json();
      console.log('Received response:', data);
      addMessage(data.response);
      speakResponse(data.response);
    } catch (error) {
      console.error('Chat error:', error);
      addMessage('Sorry, I couldn\'t process that request.');
    }
  }

  sendChat.addEventListener('click', () => {
    const message = chatInput.value.trim();
    console.log('Send button clicked, message:', message);
    if (message) sendMessage(message);
  });

  chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      const message = chatInput.value.trim();
      if (message) sendMessage(message);
    }
  });

  // Voice functionality
  if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    console.log('Speech recognition available');
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      chatInput.value = transcript;
      sendMessage(transcript);
    };

    recognition.onend = () => {
      isListening = false;
      voiceBtn.classList.remove('bg-red-600');
      voiceBtn.classList.add('bg-green-600');
    };

    voiceBtn.addEventListener('click', () => {
      console.log('Voice button clicked, isListening:', isListening);
      if (isListening) {
        recognition.stop();
      } else {
        recognition.start();
        isListening = true;
        voiceBtn.classList.remove('bg-green-600');
        voiceBtn.classList.add('bg-red-600');
      }
    });
  } else {
    console.log('Speech recognition not available');
    voiceBtn.style.display = 'none';
  }

  function speakResponse(text) {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      window.speechSynthesis.speak(utterance);
    }
  }
});
