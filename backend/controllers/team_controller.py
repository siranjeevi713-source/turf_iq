from flask import request, jsonify
from models.team_model import TeamModel
from models.notification_model import NotificationModel
from middleware.auth_middleware import token_required
from flask import Blueprint

team_bp = Blueprint("team_bp", __name__)

@team_bp.route("/create", methods=["POST"])
@token_required
def create_team():
    data = request.json
    required_fields = ["team_name", "sport", "location", "date_time", "required_players"]
    for f in required_fields:
        if f not in data:
            return jsonify({"error": f"{f} is required"}), 400

    creator_id = request.user["user_id"]
    required = int(data["required_players"])

    team_data = {
        "team_name": data["team_name"],
        "sport": data["sport"],
        "location": data["location"],
        "date_time": data["date_time"],
        "required_players": required,
        "current_players_count": 1,
        "players": [creator_id],
        "creator_id": creator_id,
        "turf_id": data.get("turf_id"),
        "slot_id": data.get("slot_id"),
        "status": "Looking for players"
    }

    result = TeamModel.create_team(team_data)
    team_id = str(result.inserted_id)
    return jsonify({
        "message": "Team created",
        "team_id": team_id,
        "players": f"1 / {required} – Need {required - 1}"
    }), 201

@team_bp.route("/", methods=["GET"])
@token_required
def get_teams():
    location = request.args.get("location")
    sport = request.args.get("sport")
    date_time = request.args.get("date_time")
    teams = TeamModel.get_all_teams(location, sport)
    return jsonify(teams), 200

@team_bp.route("/<team_id>/join", methods=["POST"])
@token_required
def join_team(team_id):
    user_id = request.user["user_id"]
    team = TeamModel.get_team_by_id(team_id)

    if not team:
        return jsonify({"error": "Team not found"}), 404
    if user_id in team.get("players", []):
        return jsonify({"error": "You are already in this team"}), 400
    if team["current_players_count"] >= team["required_players"]:
        return jsonify({"error": "Team is full"}), 400

    success = TeamModel.add_player(team_id, user_id)
    if not success:
        return jsonify({"error": "Failed to join team"}), 500

    new_count = team["current_players_count"] + 1
    required = team["required_players"]

    # Notify team creator
    NotificationModel.create(
        team["creator_id"],
        "player_joined",
        {"message": f"A new player joined your team '{team['team_name']}'", "team_id": team_id}
    )

    return jsonify({
        "message": "Successfully joined the team",
        "players": f"{new_count} / {required} – Need {required - new_count}"
    }), 200

@team_bp.route("/<team_id>", methods=["GET"])
@token_required
def get_team(team_id):
    team = TeamModel.get_team_by_id(team_id)
    if not team:
        return jsonify({"error": "Team not found"}), 404
    return jsonify(team), 200

@team_bp.route("/<team_id>/autofill", methods=["POST"])
@token_required
def autofill_team(team_id):
    """DEMO MODE: Auto-fill remaining team slots with fake users"""
    from config.db import db
    team = TeamModel.get_team_by_id(team_id)
    if not team:
        return jsonify({"error": "Team not found"}), 404
    
    needed = team["required_players"] - team["current_players_count"]
    if needed <= 0:
        return jsonify({"message": "Team is already full"}), 200
    
    # Pick random users not already in team
    existing = team.get("players", [])
    fake_users = list(db["users"].find({
        "role": "User",
        "_id": {"$nin": [__import__("bson").ObjectId(p) for p in existing]}
    }).limit(needed))
    
    added = []
    for u in fake_users:
        pid = str(u["_id"])
        TeamModel.add_player(team_id, pid)
        added.append({"id": pid, "name": u.get("name", "Player")})
    
    return jsonify({
        "message": f"Auto-filled {len(added)} demo players",
        "added_players": added
    }), 200
