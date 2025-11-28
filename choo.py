from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from pymongo import MongoClient
import requests
from datetime import datetime
import os
from bson import ObjectId
from dotenv import load_dotenv
import hashlib
import google.generativeai as genai

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-key-change-in-production")
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Load environment variables
load_dotenv(".env.local", override=False)

# Access environment variables
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Configure Gemini AI
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
    print("✓ Gemini AI configured successfully")
else:
    model = None
    print("⚠ Gemini API key not found")

# MongoDB connection setup
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command('ismaster')
    db = client['Users']
    users_collection = db['users']
    chat_history_collection = db['chat_history']
    print("✓ MongoDB connected successfully")
except Exception as e:
    print(f"⚠ MongoDB Connection Error: {e}")

def hash_password(password):
    """Hash password for security"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_hash, password):
    """Verify password"""
    return stored_hash == hashlib.sha256(password.encode()).hexdigest()

def get_weather(city):
    """Fetch weather data for a city"""
    if not WEATHER_API_KEY:
        return "⚠ Weather API key not configured"
    try:
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid={WEATHER_API_KEY}"
        response = requests.get(weather_url, timeout=5)
        if response.status_code == 200:
            weather_data = response.json()
            temp = weather_data['main']['temp']
            description = weather_data['weather'][0]['description'].capitalize()
            city_name = weather_data['name']
            country = weather_data['sys']['country']
            feels_like = weather_data['main']['feels_like']
            humidity = weather_data['main']['humidity']
            return (f"🌤 **Weather Report for {city_name}, {country}**\n"
                    f"Temperature: {temp}°C\n"
                    f"Feels Like: {feels_like}°C\n"
                    f"Condition: {description}\n"
                    f"Humidity: {humidity}%")
        return f"❌ City '{city}' not found."
    except requests.exceptions.Timeout:
        return "❌ Weather service timeout. Please try again."
    except Exception as e:
        return f"❌ Error fetching weather: {str(e)[:50]}"

def get_news(query="latest", num_articles=5):
    """Fetch news with better error handling"""
    if not NEWS_API_KEY:
        return "⚠ News API key not configured"
    
    try:
        # Use a more reliable NewsAPI endpoint
        headers = {'User-Agent': 'Mozilla/5.0'}
        news_url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&language=en&pageSize={num_articles}&apiKey={NEWS_API_KEY}"
        response = requests.get(news_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            news_data = response.json()
            
            if news_data.get('status') == 'error':
                error_msg = news_data.get('message', 'Unknown error')
                return f"❌ News API Error: {error_msg}"
            
            articles = news_data.get('articles', [])
            if not articles:
                return f"ℹ️ No news found for '{query}'."
            
            news_text = f"📰 **Top News on '{query}'**\n\n"
            for i, article in enumerate(articles, 1):
                title = article.get('title', 'No title')
                source = article.get('source', {}).get('name', 'Unknown')
                news_text += f"{i}. {title}\n   Source: {source}\n\n"
            return news_text.strip()
        else:
            return f"❌ Failed to fetch news (Status {response.status_code})"
    except requests.exceptions.Timeout:
        return "❌ News service timeout. Please try again."
    except requests.exceptions.RequestException as e:
        return f"❌ Network error: {str(e)[:50]}"
    except Exception as e:
        return f"❌ Error fetching news: {str(e)[:50]}"

# Enhanced NLP conversation with Gemini
def choo_choo_conversation(user_input, conversation_history=None):
    """Intelligent conversation using Google Gemini with NLP enhancements"""
    user_input = user_input.strip()
    user_lower = user_input.lower()
    
    # Check for specific intents first (better NLP)
    
    # Weather intent
    if any(word in user_lower for word in ['weather', 'temperature', 'climate', 'forecast', 'how is the weather']):
        if 'in' in user_lower or 'at' in user_lower or 'for' in user_lower:
            parts = user_lower.split('in' if 'in' in user_lower else ('at' if 'at' in user_lower else 'for'))
            if len(parts) > 1:
                city = parts[-1].strip().title()
                return get_weather(city)
        return get_weather("London")  # Default city
    
    # News intent
    if any(word in user_lower for word in ['news', 'headlines', 'latest news', 'breaking news', 'today news']):
        query = "latest"
        if 'in' in user_lower or 'about' in user_lower or 'on' in user_lower:
            parts = user_lower.split('in' if 'in' in user_lower else ('about' if 'about' in user_lower else 'on'))
            if len(parts) > 1:
                query = parts[-1].strip()
        return get_news(query)
    
    # Date/Time intent
    if any(word in user_lower for word in ['date', 'time', 'what is the date', 'what time', 'current time']):
        now = datetime.now()
        date = now.strftime("%A, %B %d, %Y")
        time = now.strftime("%I:%M %p")
        return f"📅 Today is {date}\n🕐 Current time is {time}"
    
    # Use Gemini AI for general conversation
    if model:
        try:
            # Build better prompt with context
            system_prompt = """You are Choo Choo, a friendly and helpful AI assistant. 
You provide clear, concise, and useful responses. You're knowledgeable, conversational, and always helpful.
Keep responses natural and not too long (2-3 sentences usually)."""
            
            # Build conversation context from history
            context = ""
            if conversation_history and len(conversation_history) > 0:
                context = "\n\nRecent conversation context:\n"
                for msg in conversation_history[-3:]:  # Last 3 exchanges
                    context += f"User: {msg.get('user', {}).get('text', '')}\n"
                    context += f"Assistant: {msg.get('bot', {}).get('text', '')}\n"
            
            prompt = f"{system_prompt}{context}\n\nUser: {user_input}\nAssistant:"
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=500,
                )
            )
            return response.text.strip() if response.text else "I'm thinking... please try again."
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return fallback_response(user_input)
    else:
        return fallback_response(user_input)

def fallback_response(user_input):
    """Simple fallback responses"""
    user_lower = user_input.lower().strip()
    
    responses = {
        "hi": "Hi there! How can I help?",
        "hello": "Hello! What can I do for you?",
        "hey": "Hey! What's up?",
        "how are you": "I'm doing great, thanks for asking!",
        "who are you": "I'm Choo Choo, your AI assistant!",
        "what can you do": "I can chat, fetch weather, get news, tell time, and much more!",
        "help": "I'm here to help! You can ask me about weather, news, time, or anything else.",
        "thanks": "You're welcome!",
        "thank you": "Happy to help!",
    }
    return responses.get(user_lower, "That's interesting! Tell me more or ask me something else.")

# Home page route
@app.route('/')
def home():
    return render_template('home.html')

# Login page route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.json
        email = data.get('email', '').lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({"message": "Email and password required."}), 400
        
        # Query the database for the user
        user = users_collection.find_one({"email": email})
        
        if not user:
            return jsonify({"message": "Oops, user does not exist."}), 404
        
        # Support both hashed and plain passwords (for migration)
        password_hash = user.get('password_hash')
        plain_password = user.get('password')
        
        if password_hash:
            if not verify_password(password_hash, password):
                return jsonify({"message": "Wrong password."}), 401
        elif plain_password:
            if plain_password != password:
                return jsonify({"message": "Wrong password."}), 401
            # Hash it for next time
            users_collection.update_one(
                {"email": email},
                {'$set': {'password_hash': hash_password(password)}, '$unset': {'password': ""}}
            )
        else:
            return jsonify({"message": "Wrong password."}), 401
        
        session.clear()
        session['email'] = email
        session['user_id'] = str(user['_id'])

        # Create a new chat session on login
        session_doc = {
            "email": email,
            "user_id": str(user['_id']),
            "title": "New Chat",
            "messages": [],
            "created_at": datetime.utcnow()
        }
        result = chat_history_collection.insert_one(session_doc)
        session['chat_session_id'] = str(result.inserted_id)

        return jsonify({"redirect_url": "/index"}), 200
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.json
        name = data.get('name', '').strip()
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        
        if not name or not email or not password:
            return jsonify({"message": "All fields are required."}), 400
        
        if len(password) < 6:
            return jsonify({"message": "Password must be at least 6 characters."}), 400
        
        # Check if the email already exists
        if users_collection.find_one({"email": email}):
            return jsonify({"message": "User already exists or try with a different email ID."}), 409
        
        # Insert the new user with hashed password
        users_collection.insert_one({
            "name": name, 
            "email": email, 
            "password_hash": hash_password(password),
            "created_at": datetime.utcnow()
        })
        return jsonify({"message": "Account Created successful"}), 200
    
    return render_template('signup.html')

# Index page route
@app.route('/index')
def index():
    if 'email' not in session:
        return redirect(url_for('login'))
    
    if 'chat_session_id' in session:
        return render_template('index.html')

    # Check if the user has previous chat sessions
    last_session = chat_history_collection.find_one(
        {"email": session['email']}, sort=[("created_at", -1)]
    )

    if last_session:
        session['chat_session_id'] = str(last_session["_id"])
    else:
        # Create a new chat session
        session_doc = {
            "email": session['email'],
            "user_id": session.get('user_id'),
            "title": "New Chat",
            "messages": [],
            "created_at": datetime.utcnow()
        }
        result = chat_history_collection.insert_one(session_doc)
        session['chat_session_id'] = str(result.inserted_id)

    return render_template('index.html')

@app.route('/hom')
def hom():
    return render_template('home.html')

@app.route('/logout')
def logout():
    session.pop('email', None)
    session.pop('chat_session_id', None)
    session.pop('user_id', None)
    return render_template('home.html')

@app.route('/new-chat', methods=['GET'])
def new_chat():
    if 'email' not in session:
        return redirect(url_for('login'))
    
    session_doc = {
        "email": session['email'],
        "user_id": session.get('user_id'),
        "title": "New Chat",
        "messages": [],
        "created_at": datetime.utcnow()
    }
    result = chat_history_collection.insert_one(session_doc)
    session['chat_session_id'] = str(result.inserted_id)
    
    return redirect(url_for('index'))

# API to get the logged-in user's email
@app.route('/api/get-email', methods=['GET'])
def get_email():
    email = session.get('email')
    if email:
        return jsonify({"email": email})
    else:
        return jsonify({"email": "Guest"})

# API to check if APIs are working
@app.route('/api/health-check', methods=['GET'])
def health_check():
    """Check if all APIs are configured and working"""
    status = {
        "gemini": "✓ OK" if GOOGLE_API_KEY and model else "✗ Not configured",
        "weather": "✓ OK" if WEATHER_API_KEY else "✗ Not configured",
        "news": "✓ OK" if NEWS_API_KEY else "✗ Not configured",
        "mongodb": "✓ OK",
    }
    return jsonify(status)

# Typed input API
@app.route('/api/typed-input', methods=['POST'])
def api_typed_input():
    data = request.json
    user_input = data.get('text', '').strip()
    session_id = data.get('sessionId') or session.get('chat_session_id')
    
    if not user_input:
        return jsonify({"error": "Empty input"}), 400
    
    # Get conversation history for context
    conversation_history = []
    if session_id:
        try:
            chat_session = chat_history_collection.find_one({'_id': ObjectId(session_id)})
            if chat_session:
                conversation_history = chat_session.get('messages', [])
        except:
            pass
    
    response = choo_choo_conversation(user_input, conversation_history)
    updated_title = None

    if session_id:
        try:
            chat_session = chat_history_collection.find_one({'_id': ObjectId(session_id)})
            if chat_session:
                messages = chat_session.get('messages', [])
                if chat_session.get('title') == "New Chat" and len(messages) == 0:
                    updated_title = " ".join(user_input.split()[:5])
                    chat_history_collection.update_one(
                        {'_id': ObjectId(session_id)},
                        {'$set': {'title': updated_title}}
                    )
                new_entry = {
                    "user": {"text": user_input},
                    "bot": {"text": response},
                    "timestamp": datetime.utcnow()
                }
                chat_history_collection.update_one(
                    {'_id': ObjectId(session_id)},
                    {'$push': {'messages': new_entry}}
                )
        except Exception as e:
            print(f"Error saving chat: {e}")

    return jsonify({"text": user_input, "response": response, "updated_title": updated_title})

# Chat History API
@app.route('/api/chat-history', methods=['GET'])
def chat_history():
    email = session.get('email')
    if not email:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        sessions_cursor = chat_history_collection.find({"email": email}).sort("created_at", -1).limit(50)
        chat_list = []
        for s in sessions_cursor:
            messages = s.get("messages", [])
            preview = messages[0].get("user", {}).get("text", "") if messages else ""
            chat_list.append({
                "chat_session_id": str(s["_id"]),
                "title": s.get("title", "No Title"),
                "created_at": s["created_at"].isoformat(),
                "preview": preview,
                "message_count": len(messages)
            })
        return jsonify({"chat_history": chat_list})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Create New Chat Session
@app.route('/api/new-session', methods=['POST'])
def new_session():
    if 'email' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        session_doc = {
            "email": session['email'],
            "user_id": session.get('user_id'),
            "title": "New Chat",
            "messages": [],
            "created_at": datetime.utcnow()
        }
        result = chat_history_collection.insert_one(session_doc)
        session['chat_session_id'] = str(result.inserted_id)
        return jsonify({"chat_session_id": str(result.inserted_id)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Get Chat Session
@app.route('/api/get-chat/<session_id>', methods=['GET'])
def get_chat(session_id):
    email = session.get('email')
    if not email:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        chat_session = chat_history_collection.find_one({'_id': ObjectId(session_id), 'email': email})
        if chat_session:
            chat_session['_id'] = str(chat_session['_id'])
            if 'created_at' in chat_session:
                chat_session['created_at'] = chat_session['created_at'].isoformat()
            return jsonify(chat_session), 200
        return jsonify({"error": "Chat not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Delete Chat Session
@app.route('/api/delete-chat/<session_id>', methods=['DELETE'])
def delete_chat(session_id):
    email = session.get('email')
    if not email:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        result = chat_history_collection.delete_one({'_id': ObjectId(session_id), 'email': email})
        if result.deleted_count > 0:
            return jsonify({"message": "Chat deleted"}), 200
        return jsonify({"error": "Chat not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
