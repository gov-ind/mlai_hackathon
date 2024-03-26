from pytestutils import *
import pytest


def test_load_submissions(db_client: LeaderboardDBClient):
    existing_submissions = db_client.load_all_submissions("team1")

    assert len(existing_submissions) == 0

def test_make_a_submission(db_client: LeaderboardDBClient):
    existing_submissions = db_client.load_all_submissions("good team")
    assert len(existing_submissions) == 0

    submission = {
        "team": "good team",
        "commit_hash": "1234",
    }

    db_client.upsert_submission(submission)
    existing_submissions = db_client.load_all_submissions("good team")
    assert len(existing_submissions) == 1

    db_client.delete_submission("good team", "1234")
    existing_submissions = db_client.load_all_submissions("good team")
    assert len(existing_submissions) == 0

def test_leaderboard_db_updates(db_client):
    team_name = "the slice and dice girls"

    submission = {
        "main_trial_idx": 0.0,
        "error_traceback": None,
        "main_trial": {
            "profits": [
                -7.979027700261019,
                3.5329587136597684,
            ],
            "socs": [
                53.75,
                52.870370370370374,
            ],
            "start_step": 0.0,
            "market_prices": [
                34.14524892893011,
                23.603033351187605,
            ],
            "timestamps": [
                1704067200, # 2024-01-01 00:00:00
                1704067500, # 2024-01-01 00:05:00
            ],
            "actions": [
                50.0,
                -50.0,
            ],
            "episode_length": 289.0
        },
        "status": "success",
        "class_name": "RandomPolicy",
        "score": 3.5329587136597684,
        "num_runs": 100.0,
        "team": team_name,
        "error": None,
        "commit_hash": "098fffa0-bf29-45ef-81c8-b10d72aa62e2"
    }

    db_client.upsert_submission(submission)
    existing_submissions = db_client.load_all_submissions(team_name)
    original_submitted_at = existing_submissions[0]['submitted_at']
    assert len(existing_submissions) == 1

    submission2 = {
        "main_trial_idx": 0.0,
        "error_traceback": None,
        "main_trial": {
            "profits": [
                2.3123123,
                1.34,
            ],
            "socs": [
                49.120370370370374,
                52.870370370370374,
            ],
            "market_prices": [
                34.14524892893011,
                23.603033351187605,
            ],
            "timestamps": [
                1704067800,
                1704068100,
            ],
            "actions": [
                50.00,
                50.00
            ],
        },
        "status": "success",
        "class_name": "RandomPolicy",
        "score": 1.34,
        "num_runs": 100.0,
        "team": team_name,
        "error": None,
        "commit_hash": "098fffa0-bf29-45ef-81c8-b10d72aa62e2"
    }

    db_client.upsert_submission(submission2)
    existing_submissions = db_client.load_all_submissions(team_name)
    assert len(existing_submissions) == 1

    updated_submission = existing_submissions[0]

    assert updated_submission['score'] == 1.34
    assert updated_submission['submitted_at'] > original_submitted_at
    assert updated_submission['main_trial']['profits'] == [-7.979027700261019, 3.5329587136597684, 2.3123123, 1.34]

    # delete all existing submissions
    db_client.delete_submission(team_name, "098fffa0-bf29-45ef-81c8-b10d72aa62e2")
    existing_submissions = db_client.load_all_submissions(team_name)
    assert len(existing_submissions) == 0

def test_leaderboard_db_prevents_bad_updates(db_client):
    team_name = "the slice and dice girls"

    submission = {
        "main_trial_idx": 0.0,
        "error_traceback": None,
        "main_trial": {
            "profits": [
                -7.979027700261019,
                3.5329587136597684,
            ],
            "socs": [
                53.75,
                52.870370370370374,
            ],
            "start_step": 0.0,
            "market_prices": [
                34.14524892893011,
                23.603033351187605,
            ],
            "timestamps": [
                1704067200, # 2024-01-01 00:00:00
                1704067500, # 2024-01-01 00:05:00
            ],
            "actions": [
                50.0,
                -50.0,
            ],
            "episode_length": 289.0
        },
        "status": "success",
        "class_name": "RandomPolicy",
        "score": 3.5329587136597684,
        "num_runs": 100.0,
        "team": team_name,
        "error": None,
        "commit_hash": "098fffa0-bf29-45ef-81c8-b10d72aa62e2"
    }

    submission2 = {
        "main_trial_idx": 0.0,
        "error_traceback": None,
        "main_trial": {
            "profits": [
                2.3123123,
                1.34,
            ],
            "socs": [
                49.120370370370374,
                52.870370370370374,
            ],
            "market_prices": [
                34.14524892893011,
                23.603033351187605,
            ],
            "timestamps": [
                1704067800,
                1704068100,
            ],
            "actions": [
                50.00,
                50.00
            ],
        },
        "status": "success",
        "class_name": "RandomPolicy",
        "score": 1.34,
        "num_runs": 100.0,
        "team": team_name,
        "error": None,
        "commit_hash": "098fffa0-bf29-45ef-81c8-b10d72aa62e2"
    }

    db_client.upsert_submission(submission)
    existing_submissions = db_client.load_all_submissions(team_name)
    assert len(existing_submissions) == 1

    empty_submission = {}
    with pytest.raises(AssertionError):
        db_client.upsert_submission(empty_submission)

    sub_off_timed = submission2.copy()
    sub_off_timed['main_trial']['timestamps'] = [1704067700, 1704068100]

    with pytest.raises(ValueError):
        db_client.upsert_submission(sub_off_timed)

    sub_off_timed["main_trial"]['timestamps'] = [1704067500, 1704067800]

    db_client.delete_submission(team_name, "098fffa0-bf29-45ef-81c8-b10d72aa62e2")
    existing_submissions = db_client.load_all_submissions(team_name)
    assert len(existing_submissions) == 0
