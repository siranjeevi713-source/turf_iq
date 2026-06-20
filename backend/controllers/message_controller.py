from flask import Blueprint, request, jsonify
from models.message_model import MessageModel
from models.team_model import TeamModel
from middleware.auth_middleware import token_required

message_bp = Blueprint("message_bp", __name__)

@message_bp.route("/<team_id>", methods=["GET"])
@token_required
def get_messages(team_id):
    """GET /messages/:team_id — fetch message history"""
    user_id = request.user["user_id"]
    # Verify user is a team member
    team = TeamModel.get_team_by_id(team_id)
    if not team:
        return jsonify({"error": "Team not found"}), 404
    if user_id not in team.get("players", []):
        return jsonify({"error": "Access denied: not a team member"}), 403

    msgs = MessageModel.get_room_messages(f"team_{team_id}")
    return jsonify(msgs), 200

@message_bp.route("/", methods=["POST"])
@token_required
def post_message():
    """POST /messages — send a message (REST fallback)"""
    data = request.json
    team_id = data.get("team_id")
    text    = data.get("text")
    if not team_id or not text:
        return jsonify({"error": "team_id and text required"}), 400

    user_id = request.user["user_id"]
    team = TeamModel.get_team_by_id(team_id)
    if not team:
        return jsonify({"error": "Team not found"}), 404
    if user_id not in team.get("players", []):
        return jsonify({"error": "Access denied: not a team member"}), 403

    from config.db import db
    user = db["users"].find_one({"_id": __import__("bson").ObjectId(user_id)})
    name = user["name"] if user else "Player"

    MessageModel.save_message(f"team_{team_id}", user_id, name, text)
    return jsonify({"message": "Message sent"}), 201
