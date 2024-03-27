import docker
import os
import subprocess
import requests
import json
import sys
import traceback

from dock import get_submission_output
from submission_backend.leaderboard_db import LeaderboardDBClient

with open('.credentials.json') as f:
    credentials = json.load(f)
GITHUB_API = "https://api.github.com"
TOKEN = credentials['GITHUB_TOKEN']
SUBMISSION_DIR = 'submissions'

REPOS = ["MLAI-AUS-Inc/trading-bot-test-team", "MLAI-AUS-Inc/trading-bot"]  # List of repositories to check

headers = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def check_submission_tags(repo_name):
    """Check if a repository has tags that contain the phrase 'submission'."""
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

def run_evaluation(submission_client, repo_name, tag_name, commit_sha, evaluation_file, present_index, repo_dir=None, clone=True):
    if repo_dir is None:
        repo_dir = f"{SUBMISSION_DIR}/{repo_name.split('/')[-1]}"
    repo_url_with_token = f"https://{TOKEN}@github.com/{repo_name}.git"
    
    current_working_directory = os.getcwd()
    output_directory = os.path.join(current_working_directory, "output")
    
    if clone:
        clone_command = f"git clone --branch {tag_name} --single-branch {repo_url_with_token} {repo_dir}"

        if os.path.exists(repo_dir):
            raise ValueError(f"The evaluation pipeline was just asked to clone into {repo_dir} but that directory already exists")
        try:
            os.system(clone_command)
            output = get_submission_output(submission_client, output_directory, repo_dir, evaluation_file, present_index)
        finally:
            os.system(f"rm -rf {repo_dir}")
    else:
        output = get_submission_output(submission_client, output_directory, repo_dir, evaluation_file, present_index)

    return output

def submit_output(docker_client, db_client, repo_name, tag_name, commit_sha, evaluation_file, present_index, repo_dir=None, clone=False):
    base_submission = {
        'team': repo_name,
        'commit_hash': commit_sha,
        'score': 0,
        'error': None,
        'error_traceback': None,
        'status': 'pending'
    }
    
    submission = base_submission.copy()
    success = db_client.submit(submission)
    if not success:
        submission = base_submission.copy()
        print(f"Failed to submit {repo_name} with commit {commit_sha}")
        submission['status'] = 'failed'
        submission['error'] = 'Failed to submit preliminary submission to database'
        db_client.submit(submission)
    try:
        submission = base_submission.copy()
        output = run_evaluation(docker_client, repo_name, tag_name, commit_sha, evaluation_file, present_index, repo_dir, clone=clone)
        for k, v in output.items():
            submission[k] = v

        submission['main_trial'] = submission['trials'][submission['main_trial_idx']]
        del submission['trials']

        submission['status'] = 'success'
    except Exception as e:
        submission = base_submission.copy()
        print(f"Failed to evaluate {repo_name} with commit {commit_sha}")
        submission['error'] = str(e)
        submission['error_traceback'] = traceback.format_exc()
        submission['status'] = 'failed'
    
    success = db_client.submit(submission)

def main():
    with open('.credentials.json') as f:
        credentials = json.load(f)

    db_client = LeaderboardDBClient(credentials['AWS_ACCESS_KEY_ID'], credentials['AWS_SECRET_ACCESS_KEY'])
    docker_client = docker.from_env()
    
    evaluation_file = os.path.join("submission_backend", "test_data.csv")
    present_index = 20

    for repo_name in REPOS:
        print('evaluating repo', repo_name)
        submission_tags = check_submission_tags(repo_name)
        for tag_name, commit_sha in submission_tags:
            if not db_client.is_already_submitted(repo_name, commit_sha):
                submit_output(docker_client, db_client, repo_name, tag_name, commit_sha, evaluation_file, present_index, clone=True)     
            else:
                print(f"Already submitted {repo_name} with commit {commit_sha}") 

if __name__ == "__main__":
    main()