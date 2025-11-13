from flask import Flask
from .views import bp as main_bp
import os

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-me")

    # Enregistre le blueprint
    app.register_blueprint(main_bp)

    # S’assure que le dossier data existe (pour la base)
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)

    return app

# Pour compatibilité si tu importes `app` directement ailleurs
app = create_app()