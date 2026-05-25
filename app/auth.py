from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from werkzeug.security import check_password_hash

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    if not data or "password" not in data:
        return jsonify({"error": "Password required"}), 400

    password = data["password"]
    stored_hash = current_app.config["ADMIN_PASSWORD_HASH"]

    if not check_password_hash(stored_hash, password):
        return jsonify({"error": "Invalid password"}), 401

    token = create_access_token(identity="admin")
    return jsonify({"token": token})


@auth_bp.route("/verify", methods=["GET"])
@jwt_required()
def verify():
    return jsonify({"valid": True, "identity": get_jwt_identity()})
