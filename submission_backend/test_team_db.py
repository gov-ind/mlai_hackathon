from team_db import TeamDB
from pytestutils import *

def test_team_db(team_db_client):
    team_id = 101
    team_1 = team_db_client.get_team(team_id)
    assert team_1 == None

    team = {
        "info_type": "team",
        "team_id": team_id,
        "github_url": "MLAI/trading-bot/camp-rock-team",
        "team_name": "camp rock",
        "city": "MEL",
    }

    team_db_client.upsert_team(team)

    team_1 = team_db_client.get_team(team_id)
    assert team_1 is not None
    assert team_1 == team

    team_db_client.delete_team(team_id)

    team_1 = team_db_client.get_team(team_id)
    assert team_1 == None