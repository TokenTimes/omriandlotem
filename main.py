from flask import Flask, render_template_string, request, jsonify
import os
from dotenv import load_dotenv
from openai import OpenAI
import requests
import re
from datetime import datetime, timedelta
from Templete import HTML_TEMPLATE
import json  # Add this at the top with other imports

app = Flask(__name__)
load_dotenv()

# API keys
COINMARKETCAP_API_KEY = os.getenv('COINMARKETCAP_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
# HTML template

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Chat context storage
conversations = {}

@app.route('/api/chat', methods=['POST'])
def chat_api():
    user_message = request.json.get('message', '').strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400
    
    # Create a new conversation
    conversation_id = max(conversations.keys(), default=0) + 1
    
    # Create system prompt for a crypto expert
    system_prompt = {
        "role": "system",
        "content": """You are a cryptocurrency expert assistant. You have two tasks:

        1. For crypto data requests, extract action and symbol, returning a JSON object:
        {"action": "price", "symbol": "BTC"}
        
        Always convert cryptocurrency names to their symbols:
        - bitcoin/Bitcoin → BTC
        - ethereum/Ethereum → ETH
        - dogecoin/Dogecoin → DOGE
        
        2. For general chat/greetings, return:
        {"action": "chat", "response": "your response here"}

        Examples:
        User: "What's bitcoin's price?"
        Return: {"action": "price", "symbol": "BTC"}
        
        User: "What is the price of bitcoin?"
        Return: {"action": "price", "symbol": "BTC"}
        
        User: "Show ETH market cap"
        Return: {"action": "market_cap", "symbol": "ETH"}
        
        User: "Hey"
        Return: {"action": "chat", "response": "Hello! I'm your crypto assistant. I can help you with cryptocurrency prices, market data, and general crypto information. What would you like to know?"}
        
        User: "Tell me about crypto"
        Return: {"action": "chat", "response": "As a crypto expert, I can tell you that cryptocurrency represents a fascinating intersection of technology, finance, and innovation..."}"""
    }
    
    try:
        # Get GPT's analysis
        chat_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                system_prompt,
                {"role": "user", "content": user_message}
            ],
            response_format={ "type": "json_object" }
        )
        
        # Parse GPT's response
        gpt_data = json.loads(chat_response.choices[0].message.content)
        action = gpt_data.get('action')
        symbol = gpt_data.get('symbol')
        
        # Print for debugging
        print(f"User message: {user_message}")
        print(f"GPT response: {gpt_data}")
        
        # Store conversation
        conversations[conversation_id] = [{"role": "user", "content": user_message}]
        
        try:
            # Handle different types of responses
            if action == "chat":
                bot_response = gpt_data.get('response')
            elif action == "price" and symbol:
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
                # Fallback to GPT for general crypto expertise
                chat_response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful cryptocurrency expert. Provide informative and friendly responses about crypto topics."},
                        {"role": "user", "content": user_message}
                    ]
                )
                bot_response = chat_response.choices[0].message.content
        except requests.exceptions.RequestException as e:
            bot_response = "I apologize, but I couldn't fetch the latest cryptocurrency data at the moment. Please try again in a few moments."
            print(f"API Error: {str(e)}")
        except Exception as e:
            bot_response = "I apologize, but I encountered an issue while processing your request. Please try rephrasing your question."
            print(f"Processing Error: {str(e)}")
            
        # Save the conversation
        conversations[conversation_id].append({"role": "assistant", "content": bot_response})
        return jsonify({"response": bot_response, "conversation_id": conversation_id})
        
    except Exception as e:
        print(f"Error: {str(e)}")
        bot_response = "I apologize, but I encountered an unexpected error. Please try again."
        conversations[conversation_id].append({"role": "assistant", "content": bot_response})
        return jsonify({"response": bot_response, "conversation_id": conversation_id})
    

    
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

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    return jsonify({"conversations": list(conversations.keys())})

@app.route('/api/conversations/<int:conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    if conversation_id not in conversations:
        return jsonify({"error": "Conversation not found"}), 404
    return jsonify({"messages": conversations[conversation_id]})

@app.route('/api/conversations/<int:conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    if conversation_id not in conversations:
        return jsonify({"error": "Conversation not found"}), 404
    del conversations[conversation_id]
    return jsonify({"status": "success"})

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    app.run(debug=True)