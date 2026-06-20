from config.db import db
from bson import ObjectId

class TeamModel:
    collection = db["teams"] if db is not None else None

    @classmethod
    def create_team(cls, team_data):
        return cls.collection.insert_one(team_data)

    @classmethod
    def get_all_teams(cls, location=None, sport=None):
        query = {}
        if location:
            query["location"] = {"$regex": location, "$options": "i"}
        if sport:
            query["sport"] = sport
            
        teams = list(cls.collection.find(query))
        for team in teams:
            team["_id"] = str(team["_id"])
        return teams

    @classmethod
    def get_team_by_id(cls, team_id):
        team = cls.collection.find_one({"_id": ObjectId(team_id)})
        if team:
            team["_id"] = str(team["_id"])
        return team
        
    @classmethod
    def add_player(cls, team_id, user_id):
        # Atomic update pushing to array and incrementing count
        result = cls.collection.update_one(
            {"_id": ObjectId(team_id)}, 
            {
                "$addToSet": {"players": user_id},
                "$inc": {"current_players_count": 1}
            }
        )
        return result.modified_count > 0
