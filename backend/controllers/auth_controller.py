from flask import request, jsonify
import bcrypt
from config.jwt_handler import sign_jwt
from models.user_model import UserModel
from models.otp_model import OtpModel

# ─────────────────────────────────────────────────
#  OTP Endpoints (used by Turf Owner flow)
# ─────────────────────────────────────────────────

def send_otp():
    """POST /auth/send-otp  →  Generate 6-digit OTP for phone"""
    data = request.json
    phone = data.get("phone")
    if not phone:
        return jsonify({"error": "phone is required"}), 400

    otp = OtpModel.generate_otp(phone)

    # For testing/demo: return the OTP in the response
    return jsonify({
        "message": "OTP sent successfully",
        "otp": otp,  # Included for testing; remove in production
        "expires_in": "5 minutes"
    }), 200


def verify_otp():
    """POST /auth/verify-otp  →  Validate OTP"""
    data = request.json
    phone = data.get("phone")
    otp   = data.get("otp")
    if not phone or not otp:
        return jsonify({"error": "phone and otp are required"}), 400

    valid = OtpModel.verify_otp(phone, otp)
    if not valid:
        return jsonify({"error": "Invalid or expired OTP"}), 401

    return jsonify({
        "message": "OTP verified successfully",
        "phone": phone,
        "verified": True
    }), 200


# ─────────────────────────────────────────────────
#  Registration  (Player: unchanged | Owner: requires OTP)
# ─────────────────────────────────────────────────

def register():
    data = request.json
    required_fields = ["name", "phone", "password", "role"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"{field} is required"}), 400

    # Turf Owner registration requires verified OTP
    if data["role"] == "Turf Owner":
        if not OtpModel.is_verified(data["phone"]):
            return jsonify({"error": "Phone not verified. Complete OTP verification first."}), 403

    existing_user = UserModel.find_by_phone(data["phone"])
    if existing_user:
        return jsonify({"error": "Phone number already exists"}), 409

    hashed_password = bcrypt.hashpw(data["password"].encode("utf-8"), bcrypt.gensalt())

    new_user = {
        "name": data["name"],
        "age": data.get("age"),
        "gender": data.get("gender"),
        "phone": data["phone"],
        "password": hashed_password.decode("utf-8"),
        "role": data["role"],  # "User" or "Turf Owner"
        "sports_interest": data.get("sports_interest", []),
        "player_level": data.get("player_level", "Beginner"),
        "location": data.get("location", ""),
        "turf_name": data.get("turf_name", ""),  # Owner-specific
        "matches_played": 0,
        "wins": 0,
        "rating": 0,
        "points": 0,
        "badges": []
    }

    result = UserModel.create_user(new_user)
    user_id = str(result.inserted_id)
    token = sign_jwt(user_id, new_user["role"])

    # Clean up OTP session
    OtpModel.clear(data["phone"])

    return jsonify({
        "message": "User registered successfully",
        "token": token,
        "user": {
            "id": user_id,
            "name": new_user["name"],
            "role": new_user["role"]
        }
    }), 201


# ─────────────────────────────────────────────────
#  Login  (unchanged – works for both roles)
# ─────────────────────────────────────────────────

def login():
    data = request.json
    if "phone" not in data or "password" not in data:
        return jsonify({"error": "Phone and password are required"}), 400

    user = UserModel.find_by_phone(data["phone"])
    if not user:
        return jsonify({"error": "Invalid phone number or password"}), 401

    if not bcrypt.checkpw(data["password"].encode("utf-8"), user["password"].encode("utf-8")):
        return jsonify({"error": "Invalid phone number or password"}), 401

    user_id = str(user["_id"])
    token = sign_jwt(user_id, user["role"])

    return jsonify({
        "message": "Login successful",
        "token": token,
        "user": {
            "id": user_id,
            "name": user["name"],
            "role": user["role"]
        }
    }), 200

def get_me():
    """GET /auth/me  →  Fetch full profile of current user"""
    # Middleware adds user to request object
    user_id = request.user.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    user = UserModel.find_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
        
    # Remove sensitive data
    user["_id"] = str(user["_id"])
    if "password" in user:
        del user["password"]
        
    return jsonify(user), 200
