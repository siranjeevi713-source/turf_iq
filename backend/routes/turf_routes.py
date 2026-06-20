from flask import request, jsonify, Blueprint
from models.turf_model import TurfModel
from middleware.auth_middleware import token_required
from bson import ObjectId

turf_bp = Blueprint("turf_bp", __name__)

@turf_bp.route("/register", methods=["POST"])
@token_required
def register_turf():
    if request.user.get("role") != "Turf Owner":
        return jsonify({"error": "Only Turf Owners can register turfs"}), 403
    data = request.json
    required = ["turf_name", "location", "phone"]
    for r in required:
        if r not in data:
            return jsonify({"error": f"{r} is required"}), 400

    turf_data = {
        "turf_name":    data["turf_name"],
        "owner_id":     request.user["user_id"],
        "location":     data["location"],
        "phone":        data["phone"],
        "lat":          data.get("lat"),
        "lng":          data.get("lng"),
        "photos":       data.get("photos", []),
        "services":     data.get("services", []),
        "price_per_hour": data.get("price_per_hour", 500)
    }
    result = TurfModel.create_turf(turf_data)
    return jsonify({"message": "Turf registered", "turf_id": str(result.inserted_id)}), 201


@turf_bp.route("/<turf_id>", methods=["PUT"])
@token_required
def update_turf(turf_id):
    """Update turf details – owner only"""
    if request.user.get("role") != "Turf Owner":
        return jsonify({"error": "Owners only"}), 403
    data = request.json
    allowed = ["turf_name", "location", "phone", "lat", "lng", "photos",
               "services", "price_per_hour"]
    update = {k: data[k] for k in allowed if k in data}
    if not update:
        return jsonify({"error": "Nothing to update"}), 400
    TurfModel.update_turf(turf_id, update)
    return jsonify({"message": "Turf updated"}), 200


@turf_bp.route("/owner", methods=["GET"])
@token_required
def get_owner_turfs():
    """Get turfs belonging to the logged-in owner"""
    if request.user.get("role") != "Turf Owner":
        return jsonify({"error": "Owners only"}), 403
    from config.db import db
    turfs = list(db["turfs"].find({"owner_id": request.user["user_id"]}))
    for t in turfs:
        t["_id"] = str(t["_id"])
    return jsonify(turfs), 200


@turf_bp.route("/", methods=["GET"])
@token_required
def get_turfs():
    location = request.args.get("location")
    turfs = TurfModel.get_all_turfs()
    if location:
        turfs = [t for t in turfs if location.lower() in t.get("location", "").lower()]
    return jsonify(turfs), 200


@turf_bp.route("/<turf_id>", methods=["GET"])
@token_required
def get_turf(turf_id):
    turf = TurfModel.get_turf_by_id(turf_id)
    if not turf:
        return jsonify({"error": "Turf not found"}), 404
    return jsonify(turf), 200
