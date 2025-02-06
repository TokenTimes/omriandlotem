from flask import Flask, render_template_string, request, jsonify
import os
from dotenv import load_dotenv
from openai import OpenAI
import requests
import re
from datetime import datetime, timedelta

app = Flask(__name__)
load_dotenv()

# API keys
COINMARKETCAP_API_KEY = os.getenv('COINMARKETCAP_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
# HTML template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>SatoshiGPT</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css" rel="stylesheet">
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #1a202c;
            color: #edf2f7;
            display: flex;
            height: 100vh;
            margin: 0;
            overflow: hidden;
        }
        .sidebar {
            width: 300px;
            background: #2d3748;
            display: flex;
            flex-direction: column;
            border-right: 1px solid #4a5568;
            padding: 10px;
            transition: transform 0.3s ease-in-out;
            position: fixed;
            left: 0;
            top: 0;
            bottom: 0;
            z-index: 1000;
        }
        .sidebar.hidden {
            transform: translateX(-100%);
        }
        .chat-container {
            flex-grow: 1;
            margin-left: 300px;
            background: #2d3748;
            display: flex;
            flex-direction: column;
            height: 100%;
            transition: margin-left 0.3s ease-in-out;
        }
        .chat-container.expanded {
            margin-left: 0;
        }
        .messages {
            flex-grow: 1;
            overflow-y: auto;
            padding: 20px;
        }
        .message {
            margin-bottom: 15px;
            display: flex;
        }
        .message.user {
            justify-content: flex-end;
        }
        .message.bot {
            justify-content: flex-start;
        }
        .bubble {
            max-width: 70%;
            padding: 10px 15px;
            border-radius: 15px;
        }
        .bubble.user {
            background: #3182ce;
            color: #fff;
        }
        .bubble.bot {
            background: #4a5568;
            color: #edf2f7;
        }
        .input-container {
            padding: 10px;
            background: #2d3748;
            display: flex;
        }
        .input-container input {
            flex-grow: 1;
            padding: 10px;
            border: none;
            border-radius: 5px;
            margin-right: 10px;
            background: #4a5568;
            color: #fff;
        }
        .input-container button {
            padding: 10px 15px;
            background: #3182ce;
            border: none;
            border-radius: 5px;
            color: #fff;
            cursor: pointer;
        }
        .input-container button:hover {
            background: #2b6cb0;
        }
        .sidebar ul {
            list-style-type: none;
            padding: 0;
        }
        .sidebar li {
            padding: 10px;
            margin: 5px 0;
            background: #4a5568;
            border-radius: 5px;
            cursor: pointer;
            color: #fff;
            text-align: center;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .sidebar li:hover {
            background: #3182ce;
        }
        .sidebar li button {
            background: transparent;
            border: none;
            color: #fff;
            cursor: pointer;
        }
        .sidebar li button:hover {
            color: #ff4d4d;
        }
        .toggle-button {
            position: absolute;
            top: 10px;
            left: 10px;
            background: #3182ce;
            color: white;
            border: none;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 1100;
        }
        .toggle-button:hover {
            background: #2b6cb0;
        }
    </style>
</head>
<body>
    <button class="toggle-button" onclick="toggleSidebar()">☰</button>
    <div class="sidebar hidden" id="sidebar">
        <h2 style="margin-top: 10px;">Conversations</h2>
        <ul id="conversations-list"></ul>
        <button onclick="createNewConversation()" style="margin-top: 10px; background: #3182ce; color: white; padding: 10px; border: none; border-radius: 5px; cursor: pointer;">New Conversation</button>
    </div>
    <div class="chat-container" id="chat-container">
        <div id="messages" class="messages"></div>
        <div class="input-container">
            <input id="message-input" type="text" placeholder="Type a message..." onkeypress="handleKeyPress(event)"/>
            <button onclick="sendMessage()">Send</button>
        </div>
    </div>

    <script>
        let currentConversationId = null;
        let sidebarVisible = true;

        function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            const chatContainer = document.getElementById('chat-container');
            sidebarVisible = !sidebarVisible;
            sidebar.classList.toggle('hidden', !sidebarVisible);
            chatContainer.classList.toggle('expanded', !sidebarVisible);
        }

        async function fetchConversations() {
            const response = await fetch('/api/conversations');
            const data = await response.json();
            const list = document.getElementById('conversations-list');
            list.innerHTML = '';
            data.conversations.forEach(id => {
                const item = document.createElement('li');
                const text = document.createElement('span');
                text.textContent = `Conversation ${id}`;
                text.style.flex = '1';
                text.onclick = () => loadConversation(id);
                
                const deleteButton = document.createElement('button');
                deleteButton.textContent = '✖';
                deleteButton.onclick = (e) => {
                    e.stopPropagation();
                    deleteConversation(id);
                };

                item.appendChild(text);
                item.appendChild(deleteButton);
                list.appendChild(item);
            });
        }

        async function createNewConversation() {
            const response = await fetch('/api/conversations', { method: 'POST' });
            const data = await response.json();
            currentConversationId = data.conversation_id;
            fetchConversations();
            loadConversation(currentConversationId);
        }

        async function deleteConversation(id) {
            const response = await fetch(`/api/conversations/${id}`, { method: 'DELETE' });
            if (response.ok) {
                if (currentConversationId === id) {
                    currentConversationId = null;
                }
                fetchConversations();
                const messagesDiv = document.getElementById('messages');
                messagesDiv.innerHTML = '';
            } else {
                alert('Failed to delete conversation.');
            }
        }

        async function loadConversation(id) {
            currentConversationId = id;
            const response = await fetch(`/api/conversations/${id}`);
            const data = await response.json();
            const messagesDiv = document.getElementById('messages');
            messagesDiv.innerHTML = '';
            data.messages.forEach(msg => addMessage(msg.role, msg.content));
        }

        async function sendMessage() {
            if (!currentConversationId) {
                alert("Please start or select a conversation.");
                return;
            }

            const input = document.getElementById('message-input');
            const message = input.value.trim();
            if (!message) return;

            addMessage('user', message);
            input.value = '';

            const response = await fetch(`/api/chat/${currentConversationId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });

            const data = await response.json();
            addMessage('bot', data.response);
        }

        function addMessage(sender, content) {
            const messagesDiv = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;

            const bubble = document.createElement('div');
            bubble.className = `bubble ${sender}`;
            bubble.textContent = content;

            messageDiv.appendChild(bubble);
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function handleKeyPress(event) {
            if (event.key === 'Enter') sendMessage();
        }

        window.onload = async function () {
            const response = await fetch('/api/conversations');
            const data = await response.json();
            if (data.conversations.length === 0) {
                await createNewConversation();
            } else {
                currentConversationId = data.conversations[0];
                loadConversation(currentConversationId);
            }
        };

        fetchConversations();
    </script>
</body>
</html>
'''

if not COINMARKETCAP_API_KEY or not OPENAI_API_KEY:
    raise ValueError("Missing required API keys. Ensure COINMARKETCAP_API_KEY and OPENAI_API_KEY are set in .env.")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Chat context storage
conversations = {}

@app.route('/api/chat/<int:conversation_id>', methods=['POST'])
def chat_api(conversation_id):
    if conversation_id not in conversations:
        return jsonify({"error": "Conversation not found"}), 404

    user_message = request.json.get('message', '').strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    # Add user message to conversation
    conversations[conversation_id].append({"role": "user", "content": user_message})

    # Detect action and symbol
    action, symbol = detect_action_and_symbol(user_message)
    bot_response = ""
    
    try:
        if action == "search_price" and symbol:
            bot_response = f"The current price of {symbol} is ${get_crypto_price(symbol):.2f}."
        elif action == "market_cap" and symbol:
            bot_response = f"The market capitalization of {symbol} is ${get_market_cap(symbol):,.2f}."
        elif action == "volume" and symbol:
            bot_response = f"The 24h trading volume of {symbol} is ${get_24h_volume(symbol):,.2f}."
        elif action == "top_gainers":
            bot_response = get_top_gainers()
        elif action == "top_losers":
            bot_response = get_top_losers()
        elif action == "historical" and symbol:
            bot_response = get_historical_price(symbol)
        else:
            bot_response = get_openai_response(conversations[conversation_id])
    except Exception as e:
        bot_response = f"Error fetching data: {str(e)}"
    
    conversations[conversation_id].append({"role": "assistant", "content": bot_response})
    return jsonify({"response": bot_response})


def detect_action_and_symbol(message):
    """Detect the action and cryptocurrency symbol from the user's message."""
    actions = {
        "search_price": ["price", "current price"],
        "market_cap": ["market cap", "capitalization"],
        "volume": ["24h volume", "trading volume"],
        "top_gainers": ["top gainers", "biggest risers"],
        "top_losers": ["top losers", "biggest losers"],
        "historical": ["historical data", "past prices"]
    }
    action, symbol = None, None
    
    for act, keywords in actions.items():
        if any(keyword in message.lower() for keyword in keywords):
            action = act
            break
    
    match = re.search(r'\b[A-Z]{3,5}\b', message)
    if match:
        symbol = match.group(0)
    return action, symbol


def fetch_crypto_data(symbol, field):
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
    headers = {'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY}
    params = {'symbol': symbol}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()['data'][symbol]['quote']['USD'][field]


def get_crypto_price(symbol):
    return fetch_crypto_data(symbol, 'price')


def get_market_cap(symbol):
    return fetch_crypto_data(symbol, 'market_cap')


def get_24h_volume(symbol):
    return fetch_crypto_data(symbol, 'volume_24h')


def get_top_cryptos(order, sort_dir='desc'):
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
    headers = {'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY}
    params = {'sort': order, 'limit': 5, 'sort_dir': sort_dir}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()['data']
    return "\n".join([f"{coin['symbol']}: {coin['quote']['USD']['percent_change_24h']:.2f}%" for coin in data[:5]])


def get_top_gainers():
    return get_top_cryptos('percent_change_24h')


def get_top_losers():
    return get_top_cryptos('percent_change_24h', 'asc')


def get_historical_price(symbol):
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/historical'
    headers = {'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY}
    params = {'symbol': symbol, 'time_start': (datetime.now() - timedelta(days=7)).isoformat()}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    return f"Price of {symbol} a week ago: ${data['data']['quotes'][0]['quote']['USD']['price']:.2f}"


def get_openai_response(conversation):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=conversation
    )
    return response.choices[0].message.content
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)


if __name__ == '__main__':
    app.run(debug=True)
