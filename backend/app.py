import os
from datetime import datetime
from flask import Flask, send_from_directory, abort
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from sqlalchemy.orm import joinedload
from flask_cors import CORS

from extensions import db, migrate
from models import Users, Request, Tool, ToolCategory, RequestedTool, ToolUsage
from config import Config
from api import api_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # --- Extensions ---
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [
                # production SPA
                getattr(Config, "FRONTEND_ORIGIN", "http://localhost:5173"),
                # local dev SPAs
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:5000",
                "http://127.0.0.1:5000",
                ],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
                "expose_headers": ["Content-Type"],
                "supports_credentials": True,
            }
        },
    )
    # --- Login manager (kept for compatibility with any API that needs current_user) ---
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'  # not used by SPA, but harmless

    @login_manager.user_loader
    def load_user(user_id):
        return Users.query.get(int(user_id))
    
    @login_manager.unauthorized_handler
    def _unauthorized():
        from flask import jsonify, request, redirect, url_for
        # Return JSON for API routes, redirect for web pages
        if request.path.startswith('/api/'):
            return jsonify({"error": "Unauthorized"}), 401
        return redirect(url_for('login'))

    # --- One-time DB setup / seeding ---
    with app.app_context():
        db.create_all()
        # Default categories (customize as you like)
        default_categories = ["Office Supplies", "Cleaning", "Furniture"]
        for name in default_categories:
            if not ToolCategory.query.filter_by(name=name).first():
                db.session.add(ToolCategory(name=name))
        db.session.commit()

    # --- Register API blueprint ---
    app.register_blueprint(api_bp)  # all /api/* routes

    # =========================
    # Serve React SPA build
    # =========================
    # Expecting frontend to be at ../frontend/dist relative to this file
    DIST_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
    app.static_folder = DIST_FOLDER
    app.static_url_path = "/"

    def _dist_exists() -> bool:
        index_path = os.path.join(DIST_FOLDER, "index.html")
        return os.path.isdir(DIST_FOLDER) and os.path.isfile(index_path)


    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_spa(path: str):
        """
        Catch-all to serve the React build. If a real static asset exists in dist, serve it.
        Otherwise, return index.html so the SPA router can handle it.
        """
        if not _dist_exists():
            # Helpful message if you forgot to build the frontend
            return (
                "Frontend build not found. Run:\n"
                "  cd ../frontend\n"
                "  npm install\n"
                "  npm run build\n",
                500,
                {"Content-Type": "text/plain; charset=utf-8"},
            )

        # Never let SPA eat API routes (defensive)
        if path.startswith("api/"):
            abort(404)

        # Serve actual static files if they exist
        absolute_target = os.path.join(DIST_FOLDER, path)
        if path and os.path.exists(absolute_target) and os.path.isfile(absolute_target):
            return send_from_directory(DIST_FOLDER, path)

        # SPA fallback
        return send_from_directory(DIST_FOLDER, "index.html")

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
