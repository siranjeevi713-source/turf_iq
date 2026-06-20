from flask import Blueprint
from controllers.auth_controller import register, login, send_otp, verify_otp, get_me
from middleware.auth_middleware import token_required

auth_bp = Blueprint("auth_bp", __name__)

auth_bp.route("/register", methods=["POST"])(register)
auth_bp.route("/login", methods=["POST"])(login)
auth_bp.route("/send-otp", methods=["POST"])(send_otp)
auth_bp.route("/verify-otp", methods=["POST"])(verify_otp)
auth_bp.route("/me", methods=["GET"])(token_required(get_me))
