from flask import Blueprint, request, jsonify
from models.review_model import ReviewModel
from middleware.auth_middleware import token_required

review_bp = Blueprint("review_bp", __name__)

@review_bp.route("/", methods=["POST"])
@token_required
def post_review():
    data = request.json
    turf_id = data.get("turf_id")
    rating = data.get("rating")
    comment = data.get("comment", "")
    if not turf_id or rating is None:
        return jsonify({"error": "turf_id and rating required"}), 400
    if not (1 <= int(rating) <= 5):
        return jsonify({"error": "Rating must be 1-5"}), 400
    user_id = request.user["user_id"]
    from config.db import db
    user = db["users"].find_one({"_id": __import__("bson").ObjectId(user_id)})
    user_name = user["name"] if user else "Player"
    review = ReviewModel.create(turf_id, user_id, user_name, int(rating), comment)
    return jsonify({"message": "Review submitted", "review": review}), 201

@review_bp.route("/<turf_id>", methods=["GET"])
@token_required
def get_reviews(turf_id):
    reviews = ReviewModel.get_for_turf(turf_id)
    avg = ReviewModel.get_average_rating(turf_id)
    return jsonify({"reviews": reviews, "average_rating": avg}), 200
