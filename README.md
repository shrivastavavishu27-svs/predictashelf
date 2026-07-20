## Predicta Shelf

**Predicta Shelf** is a full-stack, Python Flask-based web application that helps households track the expiry and freshness of everyday products - food, cosmetics, medicines, and groceries - in one centralized, intelligent dashboard.

Instead of relying on memory or sticky notes, users can log items through a simple form or by speaking naturally (e.g. *"Bought milk yesterday, it will go bad in 3 days"*), and the app automatically parses the input using AI, detects the category, calculates the expiry date, and adds it to the dashboard. It supports bilingual voice input (English and Hindi/Hinglish), making it accessible to a wider audience across India.

## Key Features
- 🗂️ **Centralized inventory dashboard** across Food, Cosmetics, Medicines, and Groceries
- 🎙️ **AI-powered voice entry** (English + Hindi/Hinglish) using Google Gemini API
- 🚦 **Color-coded status indicators** (green/yellow/red) for freshness at a glance
- 🍳 **AI-generated recipe suggestions** for ingredients nearing expiry, to reduce food waste
- ⚠️ **Toxic ingredient alerts** for cosmetics and packaged food
- 🔒 **Secure multi-user authentication** with password hashing and password recovery
- 🌗 **Dark/Light theme** support with a fully responsive UI

## Tech Stack
- **Backend:** Python 3, Flask 2.3.3 (Werkzeug 2.3.8)
- **AI:** Google Gemini API (Gemini 2.5 Flash) for voice parsing and recipe generation
- **Frontend:** HTML5, Jinja2 templates, CSS3
- **Storage:** Lightweight JSON file-based storage (no external DB required)

## Why JSON Storage?
Predicta Shelf uses structured JSON files instead of a relational database, keeping the app lightweight, portable, and easy to deploy - ideal for small-to-medium scale use without database configuration overhead.
