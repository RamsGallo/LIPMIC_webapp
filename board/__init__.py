from flask import Flask
from dotenv import load_dotenv
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from board.models import db, SLP
from markupsafe import Markup
import os
import re

load_dotenv()

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('FLASK_SECRET_KEY')

    app.API_KEY = os.getenv('GOOGLE_API_KEY')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate = Migrate(app, db)
    login_manager.init_app(app)

    from board.pages import bp
    app.register_blueprint(bp)

    @login_manager.user_loader
    def load_user(user_id):
        return SLP.query.get(int(user_id))

    login_manager.login_view = 'pages.login'  # redirect if not logged in

    @app.template_filter('format_intervention')
    def format_intervention_filter(text):
        if not text:
            return Markup("")

        # 1. Normalize newlines and replace any existing <br> tags with newlines
        text = text.replace('\r\n', '\n').replace('\r', '\n').replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')

        # Split into lines and process each line
        lines = text.split('\n')
        
        output_html_parts = []
        current_list = [] # Stores items for the current list being built
        current_list_type = None # 'ol' or 'ul'
        current_list_indent = -1 # To track indentation for nested lists

        def flush_list():
            nonlocal current_list, current_list_type, current_list_indent
            if current_list:
                # Join current list items into a list tag
                list_tag_content = "".join(current_list)
                output_html_parts.append(f"<{current_list_type}>{list_tag_content}</{current_list_type}>")
                current_list = []
                current_list_type = None
                current_list_indent = -1 # Reset indent after flushing

        for line in lines:
            stripped_line = line.strip()
            if not stripped_line: # Empty line
                flush_list() # If a list was open, close it (paragraph break)
                if output_html_parts and output_html_parts[-1] != "<p>&nbsp;</p>":
                    # Add a break if there's content before this blank line
                    output_html_parts.append("<p>&nbsp;</p>") # Or just <br> or <p></p>
                continue

            # Detect list item (numbered or bulleted)
            numbered_match = re.match(r'^\s*(\d+)\.\s*(.*)', line)
            bullet_match = re.match(r'^\s*([\*-])\s*(.*)', line) # Matches * or -

            indent = len(line) - len(line.lstrip()) # Get indentation level

            if numbered_match:
                # If changing list type or indent, flush previous list
                if current_list_type != 'ol' or (current_list_type == 'ol' and indent > current_list_indent and current_list_indent != -1):
                     flush_list()
                
                if not current_list_type: # Start a new ordered list
                    current_list_type = 'ol'
                    current_list_indent = indent
                
                content = numbered_match.group(2).strip()
                # Markdown bolding
                content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
                # Markdown italics (e.g., *text*)
                content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content)

                current_list.append(f"<li>{content}</li>")
            elif bullet_match:
                # If changing list type or indent, flush previous list
                if current_list_type != 'ul' or (current_list_type == 'ul' and indent > current_list_indent and current_list_indent != -1):
                    flush_list()
                
                if not current_list_type: # Start a new unordered list
                    current_list_type = 'ul'
                    current_list_indent = indent

                content = bullet_match.group(2).strip()
                # Markdown bolding
                content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
                # Markdown italics (e.g., *text*)
                content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content)
                
                current_list.append(f"<li>{content}</li>")
            else: # Not a list item, so it's a paragraph
                flush_list() # Close any open list

                # Markdown bolding and italics for paragraphs
                processed_line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line.strip())
                processed_line = re.sub(r'\*(.*?)\*', r'<em>\1</em>', processed_line)
                
                if processed_line:
                    output_html_parts.append(f"<p>{processed_line}</p>")

        flush_list()

        # Final assembly of all parts
        return Markup("".join(output_html_parts))

    return app