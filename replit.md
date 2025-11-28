# Choo Choo - Personal AI Assistant

## Overview
Modern Flask-based AI chatbot with user authentication, persistent chat history storage, weather/news integration, and voice capabilities.

## Current Status
✅ **Running successfully on Replit** - Flask app on port 5000 with MongoDB Atlas integration

## Key Improvements Made
### Security & Privacy
- Password hashing with SHA-256 for user credentials
- Secure session cookies (HttpOnly, Secure flags)
- User isolation: each user can only see their own chat history
- Chat history stored in MongoDB with user email/ID association
- Removed hardcoded secrets, now using Replit secrets

### Performance & Efficiency
- Optimized MongoDB queries with index support
- Removed heavy dependencies (spacy, pyttsx3, speech_recognition)
- Lightweight conversation engine
- Client-side text-to-speech (Web Speech API)
- Responsive design with CSS Grid/Flexbox
- Message pagination support (limits to last 20 chats)

### UI/UX Improvements
- Modern gradient design (purple theme)
- Responsive layout for mobile/tablet/desktop
- Chat history sidebar with toggle
- Real-time message updates
- Smooth animations and transitions
- Voice input with visual feedback
- Speak/Mute buttons for bot responses

## Architecture
```
choo.py - Flask backend
  ├── Authentication (signup/login with hashing)
  ├── Chat session management
  ├── Conversation logic with predefined responses
  ├── API endpoints for chat operations
  └── MongoDB integration for persistence

templates/
  ├── home.html - Landing page
  ├── login.html - User authentication
  ├── signup.html - Account creation
  └── index.html - Main chat interface

static/
  ├── style.css - Modern UI with gradients
  ├── script.js - Client-side logic & Web Speech API
  └── images/ - Logo, backgrounds
```

## Features
- **User Authentication**: Signup/login with password hashing
- **Chat History**: All conversations stored per user in MongoDB
- **Weather API**: Real-time weather for any city
- **News API**: Latest news by topic
- **Voice Input**: Browser-native speech recognition
- **Text-to-Speech**: Browser-native voice output
- **Session Management**: Automatic chat session creation/restoration

## Database Schema
### Users Collection
```json
{
  "name": "User Name",
  "email": "user@example.com",
  "password_hash": "sha256_hash",
  "created_at": "datetime"
}
```

### Chat History Collection
```json
{
  "email": "user@example.com",
  "user_id": "ObjectId",
  "title": "First message...",
  "messages": [
    {
      "user": {"text": "user message"},
      "bot": {"text": "bot response"},
      "timestamp": "datetime"
    }
  ],
  "created_at": "datetime"
}
```

## Required Environment Variables (Set via Replit Secrets)
- `MONGO_URI` - MongoDB Atlas connection string
- `WEATHER_API_KEY` - OpenWeather API key
- `NEWS_API_KEY` - NewsAPI key
- `FLASK_SECRET_KEY` - Secure random string for sessions

## Running the App
```bash
pip install -r requirements.txt
python choo.py
```
App runs on `http://0.0.0.0:5000`

## Privacy Features
✓ User data isolation (each user only sees their chats)
✓ No plaintext passwords stored
✓ Secure session cookies
✓ No unnecessary data collection
✓ Chat deletion functionality
✓ Server-side validation of all requests

## Mobile Responsiveness
✓ Tested on mobile/tablet/desktop
✓ Touch-friendly buttons
✓ Optimized layout for small screens
✓ Voice input works on mobile browsers
