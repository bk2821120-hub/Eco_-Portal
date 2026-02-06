@echo off
REM Production server startup script for Windows
REM This script runs the Flask app using Gunicorn (production WSGI server)

echo Starting EcoPortal with Gunicorn (Production Server)...
echo.

REM Activate virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
)

REM Set environment variables
set FLASK_ENV=production
set SECRET_KEY=your-secret-key-change-this-in-production

REM Run with Gunicorn
echo Running on http://0.0.0.0:5000
echo Press Ctrl+C to stop the server
echo.

gunicorn -c gunicorn_config.py app:app
