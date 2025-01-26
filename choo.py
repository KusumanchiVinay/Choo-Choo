from flask import Flask, render_template, request, jsonify, redirect, url_for
from pymongo import MongoClient
import speech_recognition as sr
import pyttsx3
import requests
from datetime import datetime
import spacy
import threading
from serpapi import GoogleSearch

# Create a lock for text-to-speech
tts_lock = threading.Lock()

app = Flask(__name__)

# MongoDB connection setup
client = MongoClient("mongodb+srv://chandrasekharp2004:Chandra%4022@Users.ubjlk.mongodb.net/?retryWrites=true&w=majority")
db = client['Users']  
users_collection = db['users']  

WEATHER_API_KEY = "52fe4d33963bc94f31c16ef32d0a123d" 

# SerpApi Key
SERP_API_KEY = "f0be44bddee394d12498ca4df5daaffe40c021ea45ea8015ab1c4a0f1b8f76d2"

# News API Key
NEWS_API_KEY = "50da3503ea4b41d4ad7df7757abd507f"

# Load NLP model
nlp = spacy.load("en_core_web_sm")

# Function to configure Choo Choo's voice
def set_choo_choo_voice(voice_type="female"):
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[1].id if voice_type == "female" else voices[0].id)
    engine.setProperty('rate', 150)
    engine.setProperty('volume', 1)
    return engine

# Text-to-Speech (TTS) function
def text_to_speech(text, voice_type="female"):
    def speak():
        with tts_lock:
            engine.stop()
            engine = set_choo_choo_voice(voice_type)
            engine.say(text)
            engine.runAndWait()

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


# Conversation logic for Choo Choo
def choo_choo_conversation(user_input):
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
    def get_news(api_key, country='us', category='general'):
        news_url = f"https://newsapi.org/v2/top-headlines?country={country}&category={category}&apiKey={api_key}"
        try:
            response = requests.get(news_url)
            if response.status_code == 200:
                news_data = response.json()
                articles = news_data.get('articles', [])
                if articles:
                    news_summary = "\n".join([f"* {article['title']}" for article in articles[:5]])
                    return f"Here are the top news headlines:\n{news_summary}"
                else:
                    return "No news articles found."
            else:
                return "Error fetching news. Please try again later."
        except Exception as e:
            return f"An error occurred: {e}"

    # Function to fetch current date and time
    def get_current_datetime():
        now = datetime.now()
        date = now.strftime("%A, %B %d, %Y")
        time = now.strftime("%I:%M %p")
        return f"Today is {date}, and the current time is {time}."

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
        "calculate": "Sure! Tell me what you’d like me to calculate.",
        "how old are you": "I’m timeless! But I’ve been here since you started me up.",
        "can you dance": "I can’t dance, but I can definitely play some great music for you to dance to!",
        "why are you called choo choo": "Because I’m fast, reliable, and always on track to help you!"
    }

    # Fallback to Google Search if no predefined response matches
    def google_search(query):
        try:
            search = GoogleSearch({"q": query, "api_key": SERP_API_KEY})
            results = search.get_dict()  # Fetches results as a dictionary
            organic_results = results.get("organic_results", [])
            if organic_results:
                response = []
                for result in organic_results[:5]:  # Limit to the top 5 results
                    title = result.get('title', 'No title available')
                    snippet = result.get('snippet', 'No description available')
                    response.append(f"Title: {title}\nSnippet: {snippet}\n")
                return "\n".join(response)
            return "I couldn't find any relevant information on Google."
        except Exception as e:
            return f"Error during Google Search: {e}"

    # Check for predefined responses or specific intents
    if "weather" in user_input or "temperature" in user_input:
        if "in" in user_input:
            city = user_input.split("in")[-1].strip()  # Extract city name
            if city:
                return get_weather(city, WEATHER_API_KEY)
            return "Please specify a city to check the weather."

    if "news" in user_input or "headlines" in user_input:
        return get_news(NEWS_API_KEY)

    if "date" in user_input or "time" in user_input or "today" in user_input:
        return get_current_datetime()

    # Return predefined response or fallback to Google Search
    return predefined_responses.get(user_input, google_search(user_input))


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
    return render_template('index.html')

@app.route('/hom')
def hom():
    return render_template('home.html')

# Text-to-speech API route
@app.route('/api/text-to-speech', methods=['POST'])
def api_text_to_speech():
    data = request.json
    text = data.get('text')
    voice_type = data.get('voice_type', 'female')
    text_to_speech(text, voice_type)
    return jsonify({"message": "Text has been spoken."})

# Typed input API route
@app.route('/api/typed-input', methods=['POST'])
def api_typed_input():
    data = request.json
    user_input = data.get('text')
    response = choo_choo_conversation(user_input)
    text_to_speech(response, "female")
    return jsonify({"text": user_input, "response": response})

if __name__ == '__main__':
    app.run(debug=True)