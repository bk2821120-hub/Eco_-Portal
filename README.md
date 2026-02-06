# 🌿 EcoPortal
**Deployment Update:** Forced Python 3.9 runtime to fix feedparser compatibility. - Environmental News & Awareness Platform

A comprehensive web platform for environmental news, climate awareness, and community-driven issue reporting with a modern YouTube-style community interface.

## ✨ Features
- **User Authentication**: Secure signup and login system
- **GreenMind News**: AI-enhanced environmental news with educational insights
- **YouTube-Style Community**: Modern dark-themed community feed for sharing environmental issues
- **Issue Reporting**: Report and track environmental problems in your area
- **Interactive Dashboard**: Climate data visualizations
- **Responsive Design**: Optimized for mobile, tablet, and desktop

## 🛠️ Tech Stack
- **Backend**: Flask (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: HTML5, Vanilla CSS, JavaScript
- **Production Server**: Gunicorn WSGI Server
- **Deployment**: Render-ready configuration

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup Steps
1. **Clone or download the project**
   ```bash
   cd "esm college proj"
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment**
   - Windows:
     ```bash
     .venv\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source .venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Running the Application

### Development Mode (with debug)
For local development with auto-reload and debugging:

**Option 1: Using the batch script (Windows)**
```bash
start_dev.bat
```

**Option 2: Manual command**
```bash
set FLASK_ENV=development
python app.py
```

Visit: `http://127.0.0.1:5000`

### Production Mode (with Gunicorn)
For production deployment without the development server warning:

**Option 1: Using the batch script (Windows)**
```bash
start_production.bat
```

**Option 2: Manual command**
```bash
gunicorn -c gunicorn_config.py app:app
```

**Option 3: Simple Gunicorn command**
```bash
gunicorn --bind 0.0.0.0:5000 --workers 4 app:app
```

Visit: `http://0.0.0.0:5000`

## 🔧 Configuration

### Environment Variables
Create a `.env` file or set these environment variables:

```bash
SECRET_KEY=your-secret-key-here
FLASK_ENV=production  # or 'development'
PORT=5000
```

### Gunicorn Configuration
The `gunicorn_config.py` file contains production-ready settings:
- Auto-calculated worker processes based on CPU cores
- Request timeout: 120 seconds
- Logging to stdout/stderr
- Optimized for production performance

## 📁 Project Structure
```
esm college proj/
├── app.py                    # Main Flask application
├── gunicorn_config.py        # Gunicorn production configuration
├── start_production.bat      # Production startup script
├── start_dev.bat            # Development startup script
├── requirements.txt          # Python dependencies
├── Procfile                 # Render deployment config
├── templates/               # HTML templates
│   ├── index.html
│   ├── community.html       # YouTube-style community page
│   ├── news.html
│   ├── login.html
│   └── ...
├── static/                  # Static files (CSS, JS, images)
│   └── uploads/            # User-uploaded media
└── instance/               # Database and instance files
    └── database.db
```

## 🌐 Deployment

### Deploying to Render
1. Push your code to GitHub
2. Connect your repository to Render
3. Render will automatically use the `Procfile`:
   ```
   web: gunicorn app:app
   ```
4. Set environment variables in Render dashboard

### Deploying to Other Platforms
Use the Gunicorn command:
```bash
gunicorn -c gunicorn_config.py app:app
```

## 🐛 Troubleshooting

### "WARNING: This is a development server" message
✅ **Solution**: Use Gunicorn instead of Flask's built-in server
- Run `start_production.bat` or
- Run `gunicorn -c gunicorn_config.py app:app`

### Port already in use
```bash
# Windows: Find and kill process on port 5000
netstat -ano | findstr :5000
taskkill /PID <process_id> /F
```

### Database errors
```bash
# Delete and recreate database
rm instance/database.db
python app.py  # Will auto-create database
```

## 📝 Features Guide

### Community Page (YouTube-Style)
- Dark theme with modern aesthetics
- Sidebar navigation with category filters
- Post cards with media support
- Like, comment, and share functionality
- Responsive design for all devices

### GreenMind News
- AI-enhanced environmental news
- Educational insights and impact analysis
- Category-based learning
- Search functionality

## 🤝 Contributing
This is a college project. For suggestions or improvements, please contact the development team.

## 📄 License
Educational project - All rights reserved

## 👥 Credits
Developed as part of Environmental Science & Management college project

---
**Note**: Always use production mode (Gunicorn) for deployment. Development mode is only for local testing.

