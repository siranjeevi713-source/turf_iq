from flask import Blueprint, request, jsonify
from models.notification_model import NotificationModel
from middleware.auth_middleware import token_required

notification_bp = Blueprint("notification_bp", __name__)

@notification_bp.route("/", methods=["GET"])
@token_required
def get_notifications():
    user_id = request.user["user_id"]
    notifs = NotificationModel.get_user_notifications(user_id)
    return jsonify(notifs), 200

@notification_bp.route("/<notif_id>/read", methods=["PATCH"])
@token_required
def mark_read(notif_id):
    NotificationModel.mark_read(notif_id)
    return jsonify({"message": "Marked as read"}), 200

@notification_bp.route("/read-all", methods=["PATCH"])
@token_required
def mark_all_read():
    NotificationModel.mark_all_read(request.user["user_id"])
    return jsonify({"message": "All notifications marked as read"}), 200
