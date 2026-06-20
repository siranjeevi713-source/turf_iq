from functools import wraps
from flask import request, jsonify
from config.jwt_handler import decode_jwt

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            parts = request.headers["Authorization"].split()
            if len(parts) == 2 and parts[0] == "Bearer":
                token = parts[1]
                
        if not token:
            return jsonify({"error": "Token is missing"}), 401
            
        decoded = decode_jwt(token)
        if not decoded:
            return jsonify({"error": "Token is invalid or expired"}), 401
            
        request.user = decoded
        return f(*args, **kwargs)
    return decorated
