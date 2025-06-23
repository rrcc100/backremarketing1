import os
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()  # 👈 asegurate de cargar el .env si aún no se hizo

db = SQLAlchemy()

def init_db(app):
    uri = os.getenv("DATABASE_URI")
    if not uri:
        raise RuntimeError("DATABASE_URI no está definida en el entorno")

    app.config['SQLALCHEMY_DATABASE_URI'] = uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
