from task_manager import *
import subprocess
import pytest

from leaderboard_db import LeaderboardDBClient

def docker_compose_up(directory):
    try:
        # Run docker-compose up command without changing the Python script's working directory
        subprocess.run(["docker-compose", "up", "-d"], check=True, cwd=directory)
        print("docker-compose up executed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to execute docker-compose up: {e}")


def docker_compose_down(directory):
    try:
        # Run docker-compose down command without changing the Python script's working directory
        subprocess.run(["docker-compose", "down", "--remove-orphans"], check=True, cwd=directory)
        # remove unused containers
        subprocess.run(["docker", "container", "prune", "-f"], check=True)
        # remove dangling images
        subprocess.run(["docker", "image", "prune", "-f"], check=True)
        print("docker-compose down executed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to execute docker-compose down: {e}")


@pytest.fixture(scope='session')
def database_server():
    dirname = "submission_backend"
    docker_compose_up(dirname)
    yield
    docker_compose_down(dirname)

@pytest.fixture(scope='session')
def db_client(database_server):
    with open('.credentials.json') as f:
        credentials = json.load(f)

    db = LeaderboardDBClient(credentials['AWS_ACCESS_KEY_ID'], credentials['AWS_SECRET_ACCESS_KEY'])
    db.destroy_db_and_tables()
    db = LeaderboardDBClient(credentials['AWS_ACCESS_KEY_ID'], credentials['AWS_SECRET_ACCESS_KEY'])

    yield db


@pytest.fixture(scope='session')
def tm_client(database_server):
    with open('.credentials.json') as f:
        credentials = json.load(f)

    tm_db = Database(credentials['AWS_ACCESS_KEY_ID'], credentials['AWS_SECRET_ACCESS_KEY'])
    tm_db.destroy_tables()
    tm_db = Database(credentials['AWS_ACCESS_KEY_ID'], credentials['AWS_SECRET_ACCESS_KEY'])

    tm  = TaskManager(tm_db)
    yield tm
