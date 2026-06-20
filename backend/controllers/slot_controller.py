from flask import Blueprint, request, jsonify
from models.slot_model import SlotModel
from middleware.auth_middleware import token_required

slot_bp = Blueprint("slot_bp", __name__)

@slot_bp.route("/generate", methods=["POST"])
@token_required
def generate_slots():
    """Generate slots — allowed for Turf Owners and Admin"""
    role = request.user.get("role")
    if role not in ["Turf Owner", "Admin", "System"]:
        return jsonify({"error": "Only Turf Owners or Admins can generate slots"}), 403
    data = request.json
    turf_id = data.get("turf_id")
    date = data.get("date")
    price = data.get("price", 500)
    if not turf_id or not date:
        return jsonify({"error": "turf_id and date required"}), 400
    slots = SlotModel.create_slots_for_day(turf_id, date, price)
    return jsonify({"message": f"Generated {len(slots)} slots", "slots": slots}), 201

@slot_bp.route("/", methods=["GET"])
@token_required
def get_slots():
    turf_id = request.args.get("turf_id")
    date = request.args.get("date")
    target_hour = request.args.get("target_hour")
    
    available_only = request.args.get("available", "false").lower() == "true"
    if not turf_id or not date:
        return jsonify({"error": "turf_id and date required"}), 400
        
    th_int = None
    if target_hour and target_hour != "null":
        try:
            th_int = int(target_hour.split(':')[0])
        except ValueError:
            pass

    if available_only:
        slots = SlotModel.get_available_slots(turf_id, date, target_hour=th_int)
    else:
        # Full view (used by owner dashboard) — auto-generates if empty
        slots = SlotModel.get_slots_by_turf_date(turf_id, date)
        
    is_fallback = False
    
    # Cross-turf fallback only applies for player-facing available-only queries
    if len(slots) == 0 and th_int is not None:
        fallbacks = SlotModel.get_fallback_suggestions(turf_id, date, th_int)
        if fallbacks:
            slots = fallbacks
            is_fallback = True
            
    return jsonify({
        "slots": slots,
        "is_fallback": is_fallback
    }), 200

@slot_bp.route("/<slot_id>/status", methods=["PATCH"])
@token_required
def update_slot_status(slot_id):
    """Slot status — admin and owner can modify"""
    role = request.user.get("role")
    if role not in ["Admin", "System", "Turf Owner"]:
        return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    status = data.get("status")
    if status not in ["available", "blocked", "booked"]:
        return jsonify({"error": "Status must be 'available', 'blocked', or 'booked'"}), 400
    SlotModel.update_slot_status(slot_id, status)
    return jsonify({"message": f"Slot set to {status}"}), 200

@slot_bp.route("/<slot_id>/price", methods=["PATCH"])
@token_required
def update_slot_price(slot_id):
    """Slot price — admin and owner can modify"""
    role = request.user.get("role")
    if role not in ["Admin", "System", "Turf Owner"]:
        return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    price = data.get("price")
    if not price:
        return jsonify({"error": "price required"}), 400
    SlotModel.update_slot_price(slot_id, price)
    return jsonify({"message": "Price updated"}), 200

@slot_bp.route("/<slot_id>/lock", methods=["POST"])
@token_required
def lock_slot(slot_id):
    success = SlotModel.lock_slot(slot_id, minutes=3)
    if success:
        return jsonify({"message": "Slot locked temporarily"}), 200
    return jsonify({"error": "Slot unavailable or already locked"}), 409
