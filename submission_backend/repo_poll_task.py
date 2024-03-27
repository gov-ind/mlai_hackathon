import requests
import json
import traceback
from hashlib import md5

from leaderboard_db import LeaderboardDBClient
from task_manager import *
from kickoff_task import kickoff

with open('.credentials.json') as f:
    credentials = json.load(f)
GITHUB_API = "https://api.github.com"
TOKEN = credentials['GITHUB_TOKEN']
SUBMISSION_DIR = 'submissions'
MASK = (2 ** 32 - 1)

REPOS = [
    #"MLAI-AUS-Inc/trading-bot-test-team",
    #"MLAI-AUS-Inc/trading-bot",
    "gov-ind/mlai_hackathon"
]  # List of repositories to check

def check_submission_tags(repo_name, github_token):
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    url = f"{GITHUB_API}/repos/{repo_name}/tags"
    response = requests.get(url, headers=headers)
    submission_tags = []
    print(response)
    if response.status_code == 200:
        for tag in response.json():
            print(tag)
            if 'submission' in tag['name']:
                submission_tags.append((tag['name'], tag['commit']['sha']))
    return submission_tags

def has_already_been_processed(leaderboard, team_id, commit_sha):
    if leaderboard.is_already_submitted(team_id, commit_sha):
        return True

    # TODO: task manager check if there are existing tasks related to this submission, return true if there are
    return False

def do_poll(task_id="0", unix_time=0, repos=REPOS):
    db_client = LeaderboardDBClient(credentials['AWS_ACCESS_KEY_ID'], credentials['AWS_SECRET_ACCESS_KEY'])
    task_db_client = Database(credentials['AWS_ACCESS_KEY_ID'], credentials['AWS_SECRET_ACCESS_KEY'])
    tm = TaskManager(task_db_client)

    try:
        for repo_name in repos:
            team_hash = md5(repo_name.encode()).digest()
            team_id = int.from_bytes(team_hash, "big") & MASK
            print('evaluating repo', repo_name)
            submission_tags = check_submission_tags(repo_name, credentials['GITHUB_TOKEN'])
            for tag_name, commit_sha in submission_tags:
                if not has_already_been_processed(db_client, team_id, commit_sha):
                    kickoff(team_id, repo_name, commit_sha, task_id, unix_time)            
                else:
                    print(f"Already submitted {repo_name} with commit {commit_sha}") 
        
        # TODO: kickoff another timer-polling task
    except Exception as e:
        trace = traceback.format_exc()
        e_str = f"Repo polling error: {e}, {trace}"
        #tm_raise_error(tm, task_id, e_str)
        print(e_str)

@click.command()
@click.option('--repos', help='The list of repos to check')
@click.option('--task_id', help='The task id of this task')
@click.option('--unix_start', help='The unix start time of the task')
def poll_cli(repos, task_id, unix_start):
    do_poll(repos, task_id, unix_start)

if __name__ == "__main__":
    do_poll()