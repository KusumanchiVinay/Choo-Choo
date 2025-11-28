from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from pymongo import MongoClient
import speech_recognition as sr
import pyttsx3
import requests
from datetime import datetime
import spacy
import threading
import subprocess
import webbrowser
from duckduckgo_search import DDGS
import re
from youtube_search import YoutubeSearch
import os
import glob
from bson import ObjectId
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Load environment variables from config.env
load_dotenv("config.env")

# Access environment variables
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")
  
# MongoDB connection setup
client = MongoClient(MONGO_URI)
db = client['Users']
users_collection = db['users']  

# Add this line to create a chat history collection
chat_history_collection = db['chat_history']

# Load NLP model
nlp = spacy.load("en_core_web_sm")

# Global variable to hold the current TTS engine
current_engine = None

# Function to stop the current engine if it's running
def stop_current_engine():
    global current_engine
    if current_engine:
        current_engine.stop()
        current_engine = None

# Function to configure Choo Choo's voice
def set_choo_choo_voice(voice_type="female"):
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    if voice_type == "male":
        engine.setProperty('voice', voices[0].id)
    else:
        engine.setProperty('voice', voices[1].id)
    engine.setProperty('rate', 150)
    engine.setProperty('volume', 1)
    return engine

# Text-to-Speech (TTS) function
def text_to_speech(text, voice_type="female"):
    global current_engine
    stop_current_engine()  # Stop any ongoing speech
    current_engine = set_choo_choo_voice(voice_type)
    
    def speak():
        current_engine.say(text)
        current_engine.runAndWait()
        stop_current_engine()  # Reset after speaking
    
    tts_thread = threading.Thread(target=speak)
    tts_thread.start()

# Speech-to-Text (STT) function
def speech_to_text():
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print("Listening... (Speak clearly into the microphone)")
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source)
            return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return "Sorry, I couldn't understand that."
    except sr.RequestError as e:
        return f"Request error: {e}"
    except Exception as e:
        return f"Microphone error: {e}"



def clean_text(text):
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)  # Remove special characters
    return text

# Conversation logic for Choo Choo
def choo_choo_conversation(user_input):
    user_input = clean_text(user_input)
    user_input = user_input.lower()
    doc = nlp(user_input)


    # Function to fetch weather data
    def get_weather(city, api_key):
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid={api_key}"
        try:
            response = requests.get(weather_url)
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
            return f"🚨 An error occurred: {e}"

    

    # Function to fetch current news
    def get_news(api_key, query="news", num_articles=3):
        try:
            # API Request
            news_url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&apiKey={api_key}"
            response = requests.get(news_url)
            
            # Handling API Response
            if response.status_code == 200:
                news_data = response.json()
                articles = news_data.get('articles', [])

                if not articles:
                    return f"No relevant news articles found for '{query}'."

                news_summary = []
                for i, article in enumerate(articles[:num_articles], start=1):
                    title = article.get('title', 'No title available')
                    description = article.get('description', 'No description available')

                    # Format news properly for text display
                    news_summary.append(f"{i}. 📰 {title}\n   - {description}\n")

                # Join articles with proper spacing
                return f"Here are the top {num_articles} news headlines for '{query}':\n\n" + "\n".join(news_summary)

            return f"Error fetching news: {response.status_code} - {response.reason}"

        except requests.exceptions.RequestException as e:
            return f"Network error occurred: {str(e)}"
        except Exception as e:
            return f"An unexpected error occurred: {str(e)}"
                
    
    # Function to fetch current date and time
    def get_current_datetime():
        now = datetime.now()
        date = now.strftime("%A, %B %d, %Y")
        time = now.strftime("%I:%M %p")
        return f"Today is {date}, and the current time is {time}."
    
    def play_music_on_youtube(song_name):
        results = YoutubeSearch(song_name, max_results=1).to_dict()
        if results:
            video_url = "https://www.youtube.com" + results[0]['url_suffix']
            webbrowser.open(video_url)
            return f"Playing '{song_name}' on YouTube..."
        return "Could not find the song on YouTube."

    if "play" in user_input and ("on youtube" in user_input or "in youtube" in user_input):
        song_name = user_input.replace("play", "").replace("on youtube", "").replace("in youtube", "").strip()
        if song_name:
            return play_music_on_youtube(song_name)
        return "Please specify a song name to play on YouTube."

    if "search" in user_input:
        search_query = user_input.replace("search", "").strip()
        try:
            url = f"https://www.google.com/search?q={search_query}"
            webbrowser.open(url)
            return f"Searching for '{search_query}' in Google Chrome..."
        except Exception as e:
            return f"Sorry, I couldn't search for '{search_query}'. Error: {e}"

    SEARCH_DIRECTORIES = [
    os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop"),
    os.path.join(os.path.expanduser("~"), "Documents"),
    os.path.join(os.path.expanduser("~"), "Downloads"),
    "D:\\"
    ]

    def find_file(filename, file_type=None):
        """Search for a file in predefined directories and prioritize file type if specified."""
        pdf_found = None
        image_found = None
        csv_found = None
        word_found = None
        video_found = None

        for directory in SEARCH_DIRECTORIES:
            file_paths = glob.glob(os.path.join(directory, "**", f"{filename}.*"), recursive=True)
            for file_path in file_paths:
                if file_path.lower().endswith('.pdf'):
                    pdf_found = file_path
                elif file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                    image_found = file_path
                elif file_path.lower().endswith('.csv'):
                    csv_found = file_path
                elif file_path.lower().endswith(('.doc', '.docx')):
                    word_found = file_path
                elif file_path.lower().endswith(('.mp4', '.avi', '.mkv', '.mov', '.flv')):
                    video_found = file_path

        # Prioritize file type if specified
        if file_type == 'image' and image_found:
            return image_found
        elif file_type == 'file' and pdf_found:
            return pdf_found
        elif file_type == 'csv' and csv_found:
            return csv_found
        elif file_type == 'word' and word_found:
            return word_found
        elif file_type == 'video' and video_found:
            return video_found
        elif pdf_found:  
            return pdf_found
        elif image_found:  
            return image_found
        elif csv_found: 
            return csv_found
        elif word_found: 
            return word_found
        elif video_found:
            return video_found
        return None


    def open_file(file_name):

        parts = file_name.lower().split()
        file_name = " ".join(parts[:-1])  # The file name is all parts except the last
        file_type = parts[-1]  # The last part is the file type (image, file, csv, word, or video)
        
        # Find the file (image, pdf, csv, word, or video) based on the file type
        file_path = find_file(file_name, file_type)
        
        if file_path:
            try:
                os.startfile(file_path)  
                return f"Opening {file_name} ({file_type}) in my PC..."
            except Exception as e:
                return f"Error opening file: {e}"  
        else:
            return "File not found!"


    # Example usage
    if "open" in user_input and ("in my pc" in user_input or "on my pc" in user_input):
        file_name = user_input.replace("open", "").replace("in my pc", "").replace("on my pc", "").strip()
        return open_file(file_name)
    
    else:
        if "open" in user_input:
            app_name = user_input.replace("open", "").strip()

            # Open Notepad
            if app_name == "notepad" or app_name == "notebook":
                try:
                    subprocess.Popen(["notepad.exe"])
                    return "Opening Notepad..."
                except Exception as e:
                    return f"Sorry, I couldn't open Notepad. Error: {e}"

            # Open This PC
            elif app_name == "this pc":
                try:
                    subprocess.Popen(['explorer', 'shell:::{20D04FE0-3AEA-1069-A2D8-08002B30309D}'])
                    return "Opening This PC..."
                except Exception as e:
                    return f"Sorry, I couldn't open This PC. Error: {e}"

            # Open Paint
            elif app_name == "paint":
                try:
                    subprocess.Popen(["mspaint.exe"])
                    return "Opening Paint..."
                except Exception as e:
                    return f"Sorry, I couldn't open Paint. Error: {e}"

            # Open Brave Browser
            elif app_name == "brave":
                try:
                    subprocess.Popen(["C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"])  # Update path if needed
                    return "Opening Brave Browser..."
                except Exception as e:
                    return f"Sorry, I couldn't open Brave Browser. Error: {e}"
                
            elif app_name == "calculator" or app_name == "calc":
                try:
                    subprocess.Popen(["calc.exe"])
                    return "Opening Calculator..."
                except Exception as e:
                    return f"Sorry, I couldn't open Calculator. Error: {e}"

            
            # Open Camera
            elif app_name == "camera" or app_name == "cam":
                try:
                    subprocess.Popen(["start", "microsoft.windows.camera:"], shell=True)
                    return "Opening Camera..."
                except Exception as e:
                    return f"Sorry, I couldn't open the Camera. Error: {e}"

            # For all other inputs, open Google Chrome with a search query
            else:
                try:
                    url = f"https://www.{app_name}.com"
                    webbrowser.open(url)
                    return f"Opening {app_name}..."
                except Exception as e:
                    return f"Sorry, I couldn't open {app_name}. Error: {e}"

    # Check for predefined responses or specific intents
    if "weather" in user_input or "temperature" in user_input or  "climate" in user_input:
        if "in" in user_input:
            city = user_input.split("in")[-1].strip()  # Extract city name
            if city:
                return get_weather(city, WEATHER_API_KEY)
            return "Please specify a city to check the weather."
    
    if "news" in user_input or "headlines" in user_input:
            topic = user_input.split("news")[-1].strip() if "news" in user_input else "latest news"
            return get_news(NEWS_API_KEY,query=topic)

    if "date" in user_input or "time" in user_input:
        return get_current_datetime()
    
    
    # Predefined responses
    predefined_responses = {
        "hi": "Hi, How Can I assist you.?",
        "hello": "Hello, How Can I assist you.?",
        "tell me a joke": "Why don’t skeletons fight each other? They don’t have the guts!",
        "how are you": "I’m just a bunch of codes, but I’m feeling fantastic! Thanks for asking.",
        "who are you": "I’m Choo Choo, your friendly personal assistant!",
        "what is your name": "My name is Choo Choo. I'm here to assist you!",
        "what can you do": "I can assist you with tasks, fetch news, tell jokes, and much more. Just ask!",
        "what is ai": "Artificial Intelligence is the simulation of human intelligence in machines designed to think and act like humans.",
        "tell me about yourself": "I’m Choo Choo, your AI-powered assistant created to make your life easier and more fun!",
        "do you like me": "Of course, I do! You’re my favorite person to chat with.",
        "tell me a fact": "Did you know? Honey never spoils. Archaeologists have found pots of honey in ancient Egyptian tombs that are over 3,000 years old and still perfectly edible!",
        "how old are you": "I’m timeless! But I’ve been here since you started me up.",
        "can you dance": "I can’t dance, but I can definitely play some great music for you to dance to!",
        "why are you called choo choo": "Because I’m fast, reliable, and always on track to help you!"
    }

    
    def duckduckgo_search(query):
        try:
            query = query.strip()
            if not query:
                return "Please provide a valid search query."
            
            # Perform the search
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))  # Fetch top 3 results

            # Extract the best available description
            for result in results:
                if isinstance(result, dict):
                    snippet = result.get("body") or result.get("snippet") or result.get("description")
                    if snippet and len(snippet) > 30:  # Ensure snippet is meaningful
                        return snippet
            
            return "No relevant description found. Try rephrasing your query."
        
        except Exception as e:
            return f"Error during DuckDuckGo Search: {str(e)}"

            
    # Return predefined response or fallback to Google Search
    return predefined_responses.get(user_input, duckduckgo_search(user_input))


# Home page route
@app.route('/')
def home():
    return render_template('home.html')

# Login page route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        # Query the database for the user
        user = users_collection.find_one({"email": email})
        
        if not user:
            return jsonify({"message": "Oops, user does not exist."}), 404  # User not found
        
        if user['password'] != password:
            return jsonify({"message": "Wrong password."}), 401  # Incorrect password
        
        session.clear()
        session['email']=email

        # Create a new chat session on login
        session_doc = {
            "email": email,
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
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        
        if not name or not email or not password:
            return jsonify({"message": "All fields are required."}), 400
        
        # Check if the email already exists
        if users_collection.find_one({"email": email}):
            return jsonify({"message": "User already exists or try with a different email ID."}), 409  # Email already exists
        
        # Insert the new user into the database
        users_collection.insert_one({"name": name, "email": email, "password": password})
        return jsonify({"message": "Account Created successful"}), 200
    
    return render_template('signup.html')

# Index page route
@app.route('/index')
def index():
    if 'email' not in session:
        return redirect(url_for('login'))
    
    # If the user already has a session, retain it on refresh
    if 'chat_session_id' in session:
        return render_template('index.html')

    # Check if the user has previous chat sessions
    last_session = chat_history_collection.find_one(
        {"email": session['email']}, sort=[("created_at", -1)]
    )

    if last_session:
        session['chat_session_id'] = str(last_session["_id"])  # Restore last session
    else:
        # Create a new chat session only if the user has no previous chats
        session_doc = {
            "email": session['email'],
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
    session.pop('email',None)
    session.pop('chat_session_id',None)
    return render_template('home.html')

@app.route('/new-chat', methods=['GET'])
def new_chat():
    if 'email' not in session:
        return redirect(url_for('login'))
    
    session_doc = {
        "email": session['email'],
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
        return jsonify({"email": "GU"})  # Default if no email is found

# Text-to-speech API route
@app.route('/api/text-to-speech', methods=['POST'])
def api_text_to_speech():
    data = request.json
    text = data.get('text')
    voice_type = data.get('voice_type', 'female')
    text_to_speech(text, voice_type)
    return jsonify({"message": "Text has been spoken."})

@app.route('/api/typed-input', methods=['POST'])
def api_typed_input():
    data = request.json
    user_input = data.get('text')
    session_id = data.get('sessionId') or session.get('chat_session_id')
    response = choo_choo_conversation(user_input)
    updated_title = None

    if session_id:
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
                "bot": {"text": response}
            }
            chat_history_collection.update_one(
                {'_id': ObjectId(session_id)},
                {'$push': {'messages': new_entry}}
            )

    return jsonify({"text": user_input, "response": response, "updated_title": updated_title})

# Chat History API to Return Full Chat Sessions
@app.route('/api/chat-history', methods=['GET'])
def chat_history():
    email = session.get('email')
    if not email:
        return jsonify({"error": "Unauthorized"}), 401
    sessions_cursor = chat_history_collection.find({"email": email}).sort("created_at", -1)
    chat_list = []
    for s in sessions_cursor:
        messages = s.get("messages", [])
        preview = messages[0].get("user", {}).get("text", "") if messages else ""
        chat_list.append({
            "chat_session_id": str(s["_id"]),
            "title": s.get("title", "No Title"),
            "created_at": s["created_at"].isoformat(),
            "preview": preview
        })
    return jsonify({"chat_history": chat_list})

# Create a New Chat Session
@app.route('/api/new-session', methods=['POST'])
def new_session():
    if 'email' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    session_doc = {
        "email": session['email'],
        "title": "New Chat",  # initial title; will update on first user input
        "messages": [],
        "created_at": datetime.utcnow()
    }
    result = chat_history_collection.insert_one(session_doc)
    session['chat_session_id'] = str(result.inserted_id)
    return jsonify({"chat_session_id": str(result.inserted_id)}), 200

# Retrieve a Full Chat Session
@app.route('/api/get-chat/<session_id>', methods=['GET'])
def get_chat(session_id):
    email = session.get('email')
    if not email:
        return jsonify({"error": "Unauthorized"}), 401
    chat_session = chat_history_collection.find_one({"_id": ObjectId(session_id), "email": email})
    if not chat_session:
        return jsonify({"error": "Chat session not found"}), 404
    chat_session['_id'] = str(chat_session['_id'])
    chat_session['created_at'] = chat_session['created_at'].isoformat()
    return jsonify(chat_session)

@app.route('/api/get-current-session', methods=['GET'])
def get_current_session():
    current_session_id = session.get('chat_session_id')
    return jsonify({"chat_session_id": current_session_id})

@app.route('/api/delete-chat/<session_id>', methods=['DELETE'])
def delete_chat(session_id):
    email = session.get('email')
    if not email:
        return jsonify({"error": "Unauthorized"}), 401

    result = chat_history_collection.delete_one({"_id": ObjectId(session_id), "email": email})
    
    if result.deleted_count == 1:
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Chat session not found"}),404


if __name__ == '__main__':
    app.run(debug=True)