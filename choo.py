from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from pymongo import MongoClient
import requests
from datetime import datetime
import os
from bson import ObjectId
from dotenv import load_dotenv
import hashlib

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

# Simple conversation logic
def choo_choo_conversation(user_input):
    user_input = user_input.lower().strip()
    
    def get_weather(city, api_key):
        try:
            weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid={api_key}"
            response = requests.get(weather_url, timeout=5)
            if response.status_code == 200:
                weather_data = response.json()
                temp = weather_data['main']['temp']
                description = weather_data['weather'][0]['description'].capitalize()
                city_name = weather_data['name']
                country = weather_data['sys']['country']
                feels_like = weather_data['main']['feels_like']
                humidity = weather_data['main']['humidity']
                return (f"🌤 Weather Report for {city_name}, {country}:\n"
                        f"- Temperature: {temp}°C\n"
                        f"- Feels Like: {feels_like}°C\n"
                        f"- Condition: {description}\n"
                        f"- Humidity: {humidity}%")
            elif response.status_code == 404:
                return "❌ City not found. Please check the city name."
            else:
                return "⚠ Error fetching weather data. Please try again later."
        except Exception as e:
            return f"🚨 Error: {str(e)[:50]}"

    def get_news(api_key, query="news", num_articles=3):
        try:
            news_url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&apiKey={api_key}"
            response = requests.get(news_url, timeout=5)
            
            if response.status_code == 200:
                news_data = response.json()
                articles = news_data.get('articles', [])

                if not articles:
                    return f"No relevant news articles found for '{query}'."

                news_summary = []
                for i, article in enumerate(articles[:num_articles], start=1):
                    title = article.get('title', 'No title available')
                    description = article.get('description', 'No description available')
                    news_summary.append(f"{i}. 📰 {title}\n   - {description}\n")

                return f"Here are the top {num_articles} news headlines for '{query}':\n\n" + "\n".join(news_summary)

            return f"Error fetching news: {response.status_code}"

        except Exception as e:
            return f"Error: {str(e)[:50]}"
                
    def get_current_datetime():
        now = datetime.now()
        date = now.strftime("%A, %B %d, %Y")
        time = now.strftime("%I:%M %p")
        return f"Today is {date}, and the current time is {time}."
    
    # Predefined responses
    predefined_responses = {
        "hi": "Hi, How Can I assist you.?",
        "hello": "Hello, How Can I assist you.?",
        "tell me a joke": "Why don't skeletons fight each other? They don't have the guts!",
        "how are you": "I'm just a bunch of codes, but I'm feeling fantastic! Thanks for asking.",
        "who are you": "I'm Choo Choo, your friendly personal assistant!",
        "what is your name": "My name is Choo Choo. I'm here to assist you!",
        "what can you do": "I can assist you with tasks, fetch news, tell jokes, and much more. Just ask!",
        "what is ai": "Artificial Intelligence is the simulation of human intelligence in machines.",
        "tell me about yourself": "I'm Choo Choo, your AI-powered assistant!",
        "do you like me": "Of course, I do! You're my favorite person to chat with.",
        "tell me a fact": "Did you know? Honey never spoils. Archaeologists have found honey from 3,000+ years ago still edible!",
        "how old are you": "I'm timeless! But I've been here since you started me up.",
        "can you dance": "I can't dance, but I can play great music for you!",
        "why are you called choo choo": "Because I'm fast, reliable, and always on track to help you!"
    }

    # Weather check
    if "weather" in user_input or "temperature" in user_input or "climate" in user_input:
        if "in" in user_input:
            city = user_input.split("in")[-1].strip()
            if city:
                return get_weather(city, WEATHER_API_KEY)
            return "Please specify a city to check the weather."
    
    # News check
    if "news" in user_input or "headlines" in user_input:
        topic = user_input.split("news")[-1].strip() if "news" in user_input else "latest news"
        return get_news(NEWS_API_KEY, query=topic)

    # Date/Time check
    if "date" in user_input or "time" in user_input:
        return get_current_datetime()
    
    # Return predefined response or default
    return predefined_responses.get(user_input, f"I'm not sure about that. Ask me something else!")

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
        
        if not verify_password(user.get('password_hash'), password):
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

# Typed input API
@app.route('/api/typed-input', methods=['POST'])
def api_typed_input():
    data = request.json
    user_input = data.get('text', '').strip()
    session_id = data.get('sessionId') or session.get('chat_session_id')
    
    if not user_input:
        return jsonify({"error": "Empty input"}), 400
    
    response = choo_choo_conversation(user_input)
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
        sessions_cursor = chat_history_collection.find({"email": email}).sort("created_at", -1).limit(20)
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
