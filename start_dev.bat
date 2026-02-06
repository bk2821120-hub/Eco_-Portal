@echo off
REM Development server startup script for Windows
REM This script runs the Flask app in development mode

echo Starting EcoPortal in Development Mode...
echo.

REM Activate virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
)

REM Set environment variables for development
set FLASK_ENV=development
set FLASK_DEBUG=1

REM Run Flask development server
echo Running on http://127.0.0.1:5000
echo Press Ctrl+C to stop the server
echo.

python app.py
