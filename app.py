from flask import Flask
from flask_cors import CORS
from db import init_db
from dotenv import load_dotenv
load_dotenv()
from routes.stats import stats_bp  # ✅ CORRECTO

app = Flask(__name__)
CORS(app)
init_db(app)

# Registrar rutas
app.register_blueprint(stats_bp, url_prefix="/api/stats")

# Para Render
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
