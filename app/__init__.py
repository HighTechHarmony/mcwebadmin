import os

from datetime import timedelta
from flask import Flask, jsonify, request, send_from_directory
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO

socketio = SocketIO()


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)

    jwt = JWTManager(app)

    # ------------------------------------------------------------------ #
    # JWT error handlers — always return JSON                              #
    # ------------------------------------------------------------------ #
    @jwt.expired_token_loader
    def expired_token(_header, _payload):
        return jsonify({"error": "Token has expired"}), 401

    @jwt.unauthorized_loader
    def missing_token(_error):
        return jsonify({"error": "Authentication required"}), 401

    @jwt.invalid_token_loader
    def invalid_token(_error):
        return jsonify({"error": "Invalid token"}), 401

    # ------------------------------------------------------------------ #
    # Socket.IO                                                            #
    # ------------------------------------------------------------------ #
    socketio.init_app(
        app,
        cors_allowed_origins="*",
        async_mode="gevent",
        logger=False,
        engineio_logger=False,
    )

    # ------------------------------------------------------------------ #
    # Blueprints                                                           #
    # ------------------------------------------------------------------ #
    from .auth import auth_bp
    from .server import server_bp
    from .console import console_bp
    from .mods import mods_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(server_bp)
    app.register_blueprint(console_bp)
    app.register_blueprint(mods_bp)

    # ------------------------------------------------------------------ #
    # Socket.IO event registration + log-tail background thread           #
    # ------------------------------------------------------------------ #
    from . import socket_events

    socket_events.register(socketio, app.config["LOG_PATH"])

    # ------------------------------------------------------------------ #
    # SPA catch-all — serves the built React app in production            #
    # ------------------------------------------------------------------ #
    dist_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
    dist_dir = os.path.realpath(dist_dir)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_spa(path):
        if not os.path.isdir(dist_dir):
            return (
                jsonify(
                    {
                        "error": "Frontend not built.",
                        "hint": "cd frontend && npm install && npm run build",
                    }
                ),
                503,
            )
        target = os.path.join(dist_dir, path)
        if path and os.path.exists(target):
            return send_from_directory(dist_dir, path)
        return send_from_directory(dist_dir, "index.html")

    return app
