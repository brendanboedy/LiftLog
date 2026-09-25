"""Starts the LiftLog website on your computer.

Run it with:  python run.py
Then open http://127.0.0.1:5000 in your browser. Press Ctrl+C to stop.
"""
import os

from dotenv import load_dotenv

# Read settings (SECRET_KEY, DATABASE_URL...) from the .env file before the app is built.
load_dotenv()

from app import create_app  # noqa: E402  (must come after load_dotenv)

app = create_app()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
