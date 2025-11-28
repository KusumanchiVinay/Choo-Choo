# Choo Choo - Personal AI Assistant

## Overview
Flask-based AI chatbot with authentication, chat history, and multi-feature support (weather, news, file search, web search).

## Recent Changes
- Set up for Replit deployment
- Fixed security issues: environment variables and secrets management
- Removed Windows-specific functionality
- Optimized dependencies and code

## Key Features
- User authentication and chat history
- AI conversation engine with NLP
- Weather and news integration
- Voice capabilities (TTS)
- Web search functionality

## Setup for Replit
- Uses port 5000 (Flask dev server)
- MongoDB Atlas connection via environment variable
- All secrets managed via Replit secrets system
- Frontend configured for proxy access

## Required Secrets
- MONGO_URI: MongoDB connection string
- WEATHER_API_KEY: OpenWeather API key
- NEWS_API_KEY: NewsAPI key
- FLASK_SECRET_KEY: Secure session key
