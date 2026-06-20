from flask import request, jsonify
from models.turf_model import TurfModel
from middleware.auth_middleware import token_required
from bson import ObjectId

@token_required
def register_turf():
    if request.user.get("role") != "Turf Owner":
        return jsonify({"error": "Only Turf Owners can register turfs"}), 403
        
    data = request.json
    required = ["name", "turf_name", "location", "phone"]
    for r in required:
        if r not in data:
            return jsonify({"error": f"{r} is required"}), 400
            
    turf_data = {
        "turf_name": data["turf_name"],
        "owner_id": request.user["user_id"],
        "location": data["location"],
        "phone": data["phone"],
        "photos": data.get("photos", []),
        "slots": [], # {time: "10:00", status: "Available"}
        "services": data.get("services", []) # {name: "Water", price: 20}
    }
    
    result = TurfModel.create_turf(turf_data)
    return jsonify({"message": "Turf registered successfully", "turf_id": str(result.inserted_id)}), 201

@token_required
def get_turfs():
    loc = request.args.get("location")
    if loc:
        turfs = TurfModel.get_turfs_by_location(loc)
        # DEMO MODE: Auto-Generate Turfs if empty
        if not turfs:
            TurfModel.generate_virtual_turfs(loc)
            turfs = TurfModel.get_turfs_by_location(loc)
    else:
        turfs = TurfModel.get_all_turfs()
    return jsonify(turfs), 200

@token_required
def get_turf(turf_id):
    turf = TurfModel.get_turf_by_id(turf_id)
    if not turf:
        return jsonify({"error": "Turf not found"}), 404
    return jsonify(turf), 200
