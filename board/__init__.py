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

    UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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
        """
        Format intervention text with proper HTML structure for PDF rendering.
        Handles numbered sections, bullet points, actions, and sources.
        """
        if not text:
            return Markup("")
        
        # Normalize line breaks and whitespace
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = text.strip()
        
        # Convert markdown formatting to HTML
        text = re.sub(r'\*\*([^*]+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'(?<!\*)\*(?!\*)([^*]+?)\*(?!\*)', r'<em>\1</em>', text)
        text = re.sub(r'^\s*\*\s+', '• ', text, flags=re.MULTILINE)
        
        formatted_parts = []
        
        # Split by numbered sections
        section_pattern = r'(?=^\d+\.\s+)'
        sections = re.split(section_pattern, text, flags=re.MULTILINE)
        
        for section in sections:
            if not section.strip():
                continue
            
            # Check if this is a numbered section
            section_match = re.match(r'^(\d+)\.\s+(.+?):\s*\n(.*)$', section, re.DOTALL)
            
            if section_match:
                num, title, content = section_match.groups()
                
                # Remove HTML tags from title
                title_clean = re.sub(r'<[^>]+>', '', title).strip()
                
                # Start section container
                formatted_parts.append(f'<div class="intervention-section">')
                formatted_parts.append(f'<div class="intervention-number">{num}. {title_clean}:</div>')
                formatted_parts.append('<div class="intervention-actions">')
                
                # Split content by lines and process
                lines = content.strip().split('\n')
                i = 0
                
                while i < len(lines):
                    line = lines[i].strip()
                    
                    if not line:
                        i += 1
                        continue
                    
                    # Check for Action: or Source:
                    action_match = re.match(r'^(•\s*)?Action:\s*(.*)$', line)
                    source_match = re.match(r'^(•\s*)?(Source|Reference):\s*(.*)$', line)
                    
                    if action_match:
                        # Collect the full action text
                        action_text = action_match.group(2).strip()
                        i += 1
                        
                        # Continue collecting lines
                        while i < len(lines):
                            next_line = lines[i].strip()
                            if not next_line or re.match(r'^(•\s*)?(Action|Source|Reference):', next_line):
                                break
                            action_text += ' ' + next_line
                            i += 1
                        
                        # Add spacing before bullet (except for first item)
                        if formatted_parts and formatted_parts[-1] != '<div class="intervention-actions">':
                            formatted_parts.append('<div class="action-spacing"></div>')
                        
                        formatted_parts.append(
                            f'<div class="intervention-action-item">• <strong>Action:</strong> {action_text}</div>'
                        )
                    
                    elif source_match:
                        # Collect the full source text
                        source_type = source_match.group(2)
                        source_text = source_match.group(3).strip()
                        i += 1
                        
                        # Continue collecting lines
                        while i < len(lines):
                            next_line = lines[i].strip()
                            if not next_line or re.match(r'^(•\s*)?(Action|Source|Reference):', next_line):
                                break
                            source_text += ' ' + next_line
                            i += 1
                        
                        formatted_parts.append(
                            f'<div class="intervention-source">• <strong>{source_type}:</strong> {source_text}</div>'
                        )
                    
                    else:
                        # Regular text line
                        if line:
                            formatted_parts.append(f'<div class="intervention-text">{line}</div>')
                        i += 1
                
                formatted_parts.append('</div>')  # Close intervention-actions
                formatted_parts.append('</div>')  # Close intervention-section
            
            else:
                # Not a numbered section - introductory paragraph
                paragraphs = section.strip().split('\n\n')
                for para in paragraphs:
                    para = para.strip()
                    if para:
                        para = re.sub(r'\n', ' ', para)
                        formatted_parts.append(f'<p class="intervention-intro">{para}</p>')
        
        return Markup('\n'.join(formatted_parts))


    return app