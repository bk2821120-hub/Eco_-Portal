
# 🚀 Deployment Guide for EcoPortal

Your project is fully configured for deployment on **Render.com**.

## 1. Prepare your GitHub
1.  Create a new repository on GitHub.
2.  Upload/Push all your project files to this repository.
    *   *Note: Do not upload the `.venv` folder or `__pycache__`.*

## 2. Deploy on Render (Free)
1.  Go to [dashboard.render.com](https://dashboard.render.com).
2.  Click **New +** -> **Web Service**.
3.  Select **Build and deploy from a Git repository**.
4.  Connect your GitHub account and select your **EcoPortal** repository.
5.  **Configure the Service:**
    *   **Name:** `eco-portal-demo` (or any name)
    *   **Region:** Singapore (or nearest to you)
    *   **Branch:** `main` (or master)
    *   **Runtime:** `Python 3`
    *   **Build Command:** `pip install -r requirements.txt`
    *   **Start Command:** `gunicorn -c gunicorn_config.py app:app`
    *   **Instance Type:** Free

6.  Click **Create Web Service**.

## ⚠️ Important Notes
*   **Database Reset:** On the free plan, Render will restart your server roughly every 24 hours. When this happens, **your database will be reset** to empty, and any uploaded images will be deleted. This is normal for free hosting.
*   **Wait for it:** The first build might take 2-3 minutes. Watch the "Logs" tab.
*   **Success:** When you see "Your service is live", click the URL at the top (e.g., `https://eco-portal-demo.onrender.com`).

## 🎉 Done!
Your site handles static files (CSS/Images) automatically using `whitenoise`, which I have already installed for you.
