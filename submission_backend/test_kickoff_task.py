import shutil
import docker
import json
from kickoff_task import kickoff

from pytestutils import *

def test_kickoff(tm_client: TaskManager, team_db_client):
    with open('.credentials.json') as f:
        credentials = json.load(f)

    task_db = Database(credentials['AWS_ACCESS_KEY_ID'], credentials['AWS_SECRET_ACCESS_KEY'])
    tm = TaskManager(task_db)

    task_id = tm_client.database.create_task("kickoff task")
    tasks = tm_client.database.get_tasks()
    assert len(tasks) == 1

    team_id = 1
    kickoff(team_id, "trading-bot", "2c4459b9db9a9467f3f954b052eb45bde3268432", str(task_id), 0)

    reloaded_task = tm.database.get_task(task_id)
    assert reloaded_task['state_'] == 'success', reloaded_task

    tasks = tm_client.database.get_tasks()
    assert len(tasks) == 2

    tm.database.delete_task(task_id)
    # delete submission_backend/submissions even if not empty

    shutil.rmtree('submission_backend/submissions')
    # delete docker image
    client = docker.from_env()
    client.images.remove(str(team_id))