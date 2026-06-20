from flask import Blueprint, request, jsonify
from models.payment_model import PaymentModel
from models.booking_model import BookingModel
from models.slot_model import SlotModel
from models.notification_model import NotificationModel
from middleware.auth_middleware import token_required
from bson import ObjectId
from config.db import db

payment_bp = Blueprint("payment_bp", __name__)

# ────────────────────────────────────────────────
# Single or initiate-split payment
# ────────────────────────────────────────────────
@payment_bp.route("/", methods=["POST"])
@token_required
def create_payment():
    data      = request.json
    booking_id = data.get("booking_id")
    method     = data.get("method", "single")
    player_ids = data.get("player_ids", [request.user["user_id"]])
    amount     = data.get("total_amount", 0)

    if not booking_id:
        return jsonify({"error": "booking_id required"}), 400

    if method == "single":
        payment = PaymentModel.create_single_payment(booking_id, request.user["user_id"], amount)
        _confirm_booking(booking_id)
        return jsonify({
            "message": "Payment successful",
            "payment": payment,
            "txn_id": payment["txn_id"]
        }), 201

    elif method == "split":
        if not player_ids:
            return jsonify({"error": "player_ids required for split payment"}), 400
        # Prevent duplicate split init
        existing = PaymentModel.get_payments_for_booking(booking_id)
        if existing:
            return jsonify({"error": "Split payments already created for this booking"}), 409
        payments = PaymentModel.create_split_payments(booking_id, player_ids, amount)
        return jsonify({
            "message": "Split payment created. Each player must pay their share.",
            "payments": payments,
            "per_player": round(amount / len(player_ids), 2)
        }), 201

    return jsonify({"error": "Invalid method. Use 'single' or 'split'"}), 400


# ────────────────────────────────────────────────
# GET /payments/:booking_id — full payment status
# ────────────────────────────────────────────────
@payment_bp.route("/<booking_id>", methods=["GET"])
@token_required
def get_booking_payments(booking_id):
    payments    = PaymentModel.get_payments_for_booking(booking_id)
    all_paid    = PaymentModel.all_paid(booking_id)
    total_paid  = sum(p["amount"] for p in payments if p["status"] == "paid")
    total_needed = sum(p["amount"] for p in payments)
    return jsonify({
        "payments":      payments,
        "all_paid":      all_paid,
        "total_paid":    total_paid,
        "total_needed":  total_needed,
        "total_pending": total_needed - total_paid
    }), 200


# ────────────────────────────────────────────────
# POST /payments/:payment_id/pay — individual member pays
# ────────────────────────────────────────────────
@payment_bp.route("/<payment_id>/pay", methods=["POST"])
@token_required
def pay_split(payment_id):
    user_id = request.user["user_id"]
    pay = db["payments"].find_one({"_id": ObjectId(payment_id)})
    if not pay:
        return jsonify({"error": "Payment record not found"}), 404
    if pay["user_id"] != user_id:
        return jsonify({"error": "This payment does not belong to you"}), 403
    if pay["status"] == "paid":
        return jsonify({"error": "Already paid"}), 409

    result = PaymentModel.confirm_split_payment(payment_id)
    if result.modified_count == 0:
        return jsonify({"error": "Could not process payment"}), 500

    booking_id = pay["booking_id"]
    all_paid   = PaymentModel.all_paid(booking_id)

    if all_paid:
        _confirm_booking(booking_id)
        # Notify all team members booking is confirmed
        booking = db["bookings"].find_one({"_id": ObjectId(booking_id)})
        if booking and booking.get("team_id"):
            from models.team_model import TeamModel
            team = TeamModel.get_team_by_id(booking["team_id"])
            if team:
                for pid in team.get("players", []):
                    NotificationModel.create(pid, "booking_confirmed", {
                        "message": "🎉 All players paid! Booking confirmed.",
                        "booking_id": booking_id,
                        "team_id": booking["team_id"]
                    })
        return jsonify({"message": "✅ Your payment confirmed. All players paid — Booking CONFIRMED!", "booking_confirmed": True}), 200

    # Notify team about partial payment
    booking = db["bookings"].find_one({"_id": ObjectId(booking_id)})
    if booking and booking.get("team_id"):
        from models.team_model import TeamModel
        team = TeamModel.get_team_by_id(booking["team_id"])
        if team:
            user = db["users"].find_one({"_id": ObjectId(user_id)})
            name = user["name"] if user else "A player"
            for pid in team.get("players", []):
                if pid != user_id:
                    NotificationModel.create(pid, "player_paid", {
                        "message": f"💰 {name} paid their share. Waiting for others.",
                        "booking_id": booking_id
                    })

    payments    = PaymentModel.get_payments_for_booking(booking_id)
    total_paid  = sum(p["amount"] for p in payments if p["status"] == "paid")
    total_needed = sum(p["amount"] for p in payments)

    return jsonify({
        "message": "Your payment confirmed. Waiting for other players.",
        "booking_confirmed": False,
        "total_paid":  total_paid,
        "total_needed": total_needed
    }), 200


def _confirm_booking(booking_id):
    db["bookings"].update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"payment_status": "paid", "status": "Confirmed"}}
    )
    booking = db["bookings"].find_one({"_id": ObjectId(booking_id)})
    if booking and booking.get("slot_id"):
        SlotModel.book_slot(booking["slot_id"], booking.get("team_id"), booking_id)
