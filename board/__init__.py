from flask import Flask
from board import pages

def create_app():
    app = Flask(__name__)
    app.secret_key = 'iliekturtles'
    app.register_blueprint(pages.bp)
    
    return app