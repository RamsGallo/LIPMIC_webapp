from flask import Flask
from dotenv import load_dotenv
from board import pages
import os

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('FLASK_SECRET_KEY')
    app.register_blueprint(pages.bp)

    return app