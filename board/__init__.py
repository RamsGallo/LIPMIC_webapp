from flask import Flask
from dotenv import load_dotenv
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from board.models import db, SLP
import os

load_dotenv()

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('FLASK_SECRET_KEY')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)

    from board.pages import bp
    app.register_blueprint(bp)

    @login_manager.user_loader
    def load_user(user_id):
        return SLP.query.get(int(user_id))

    login_manager.login_view = 'pages.login'  # redirect if not logged in

    return app