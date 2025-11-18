import os
from flask import Flask
from dotenv import load_dotenv
from .extensions import init_extensions

def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24).hex())
    
    init_extensions()
    
    from .routes_auth import auth_bp
    app.register_blueprint(auth_bp)
    from .routes_main import main_bp
    app.register_blueprint(main_bp)
    from .routes_mindfulness import mindfulness_bp
    app.register_blueprint(mindfulness_bp)
    from .routes_yoga import yoga_bp
    app.register_blueprint(yoga_bp)
    from .routes_ai_workouts import ai_workouts_bp
    app.register_blueprint(ai_workouts_bp)
    from .routes_webcam import webcam_bp
    app.register_blueprint(webcam_bp)
    from .adaptive_plans import adaptive_bp
    app.register_blueprint(adaptive_bp)

    return app