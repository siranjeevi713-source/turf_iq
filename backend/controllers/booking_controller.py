from flask import request, jsonify
from models.booking_model import BookingModel
from models.slot_model import SlotModel
from models.notification_model import NotificationModel
from middleware.auth_middleware import token_required
from flask import Blueprint
import datetime

booking_bp = Blueprint("booking_bp", __name__)

@booking_bp.route("/create", methods=["POST"])
@token_required
def create_booking():
    data = request.json
    user_id = request.user["user_id"]
    turf_id = data.get("turf_id")
    slot_id = data.get("slot_id")
    date = data.get("date")
    services = data.get("services", [])
    total_cost = data.get("total_cost", 0)
    team_id = data.get("team_id")
    payment_method = data.get("payment_method", "single")
    player_ids = data.get("player_ids", [user_id])

    if not turf_id or not slot_id or not date:
        return jsonify({"error": "turf_id, slot_id and date required"}), 400

    # Check slot availability atomically
    slot = SlotModel.get_by_id(slot_id)
    if not slot:
        return jsonify({"error": "Slot not found"}), 404
    if slot["status"] != "available":
        return jsonify({"error": "Slot already booked or blocked. Choose another."}), 409

    booking = {
        "user_id": user_id,
        "team_id": team_id,
        "turf_id": turf_id,
        "slot_id": slot_id,
        "date": date,
        "services": services,
        "total_cost": total_cost,
        "payment_method": payment_method,
        "payment_status": "pending",
        "status": "Pending Payment",
        "created_at": datetime.datetime.utcnow()
    }

    result = BookingModel.create_booking(booking)
    booking_id = str(result.inserted_id)

    return jsonify({
        "message": "Booking created. Proceed to payment.",
        "booking_id": booking_id,
        "total_cost": total_cost,
        "payment_method": payment_method
    }), 201

@booking_bp.route("/my", methods=["GET"])
@token_required
def my_bookings():
    user_id = request.user["user_id"]
    from config.db import db
    bookings = list(db["bookings"].find({"user_id": user_id}).sort("created_at", -1))
    for b in bookings:
        b["_id"] = str(b["_id"])
        if "created_at" in b:
            b["created_at"] = b["created_at"].isoformat()
    return jsonify(bookings), 200

@booking_bp.route("/owner", methods=["GET"])
@token_required
def owner_bookings():
    if request.user.get("role") != "Turf Owner":
        return jsonify({"error": "Owners only"}), 403
    user_id = request.user["user_id"]
    from config.db import db
    # Get turfs belonging to this owner
    turfs = list(db["turfs"].find({"owner_id": user_id}))
    turf_ids = [str(t["_id"]) for t in turfs]
    bookings = list(db["bookings"].find({"turf_id": {"$in": turf_ids}}).sort("created_at", -1))
    for b in bookings:
        b["_id"] = str(b["_id"])
        if "created_at" in b:
            b["created_at"] = b["created_at"].isoformat()
    return jsonify(bookings), 200

@booking_bp.route("/<booking_id>/accept", methods=["PATCH"])
@token_required
def accept_booking(booking_id):
    from config.db import db
    from bson import ObjectId
    db["bookings"].update_one({"_id": ObjectId(booking_id)}, {"$set": {"owner_status": "accepted"}})
    return jsonify({"message": "Booking accepted"}), 200

@booking_bp.route("/<booking_id>/reject", methods=["PATCH"])
@token_required
def reject_booking(booking_id):
    from config.db import db
    from bson import ObjectId
    booking = db["bookings"].find_one({"_id": ObjectId(booking_id)})
    if booking and booking.get("slot_id"):
        SlotModel.update_slot_status(booking["slot_id"], "available")
    db["bookings"].update_one({"_id": ObjectId(booking_id)}, {"$set": {"owner_status": "rejected", "status": "Rejected"}})
    return jsonify({"message": "Booking rejected, slot freed"}), 200
