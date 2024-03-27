import docker
import traceback
import platform


import click
from task_manager import *
from task_manager_utils import tm_raise_error
SUBMISSION_DIR = 'submission_backend/submissions'

LEADERBOARD_END_DATE = 1625097600

def get_default_platform() -> str:
    machine = platform.uname().machine
    machine = {"x86_64": "amd64"}.get(machine, machine)
    return f"linux/{machine}"


def current_submission_exists_for_team(tm: TaskManager, team_id:int):
    # x = tm.database.get_tasks_for_team(team_id)
    # TODO: task manager to get all tasks for this team, see if any kickoff tasks exist as "success" and the latest one was a success
    return False


def clone_and_checkout(repo_url_with_token, repo_dir, commit_hash):
    try:
        # Execute the Git clone command
        subprocess.check_call(['git', 'clone', '--single-branch', repo_url_with_token, repo_dir])
        
        # Change directory and checkout specific commit
        subprocess.check_call(['git', '-C', repo_dir, 'checkout', commit_hash])
        
        print("Repository cloned and checked out successfully.")
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error cloning repository: {e}")

def kickoff(team_id:str, team_repo:str, commit_hash:str, task_id:str, unix_start:int):
    with open('.credentials.json') as f:
        credentials = json.load(f)

    task_db = Database(credentials['AWS_ACCESS_KEY_ID'], credentials['AWS_SECRET_ACCESS_KEY'])
    tm = TaskManager(task_db)

    try:
        tm.database.update_task(task_id, {"state_": 'running'})

        # TODO: task manager gather all tasks for this team and stop them
        repo_dir = f"{SUBMISSION_DIR}/{team_repo}"
        client = docker.from_env()

        if current_submission_exists_for_team(tm, team_repo):
            os.rmdir(repo_dir)
            client.images.remove(team_repo)
        
        repo_url_with_token = f"https://{credentials['GITHUB_TOKEN']}@github.com/MLAI-AUS-Inc/{team_repo}.git"
        repo_url_with_token = f"https://{credentials['GITHUB_TOKEN']}@github.com/{team_repo}.git"
        clone_and_checkout(repo_url_with_token, repo_dir, commit_hash)

        print('### Building image', repo_dir)
        result = client.images.build(path=repo_dir + '/bot', tag=str(team_id), platform=get_default_platform(), quiet=False)
        print(result[0], type(result[0]))
        print(dir(result[0]))

        for item in result[1]:
            print(item)

        create_eval_task(tm, team_id, commit_hash, unix_start, LEADERBOARD_END_DATE)
        tm.database.update_task(task_id, {"state_": 'success'})
    except Exception as e:
        trace = traceback.format_exc()
        task = tm.database.get_task(task_id)
        e_str = f"Submission Kickoff Error: {e}, {trace}"
        tm_raise_error(tm, task['id'], e_str)
        print(e_str)

def create_eval_task(tm: TaskManager, team_id:int, commit_hash:str, unix_start:int, unix_end:int):
    new_task_id = tm.database.create_task("PLACEHOLDER")
     
    tm.database.update_task(new_task_id, 
                            {"command": f"python submission_backend/eval_task.py --team_id {team_id} --commit_hash {commit_hash} --task_id {new_task_id} --unix_start {unix_start} --batch_unix_end {unix_end} --docker_image_tag {str(team_id)}"})

@click.command()
@click.option('--team_name', help='The name of the team to kickoff')
@click.option('--repo_dir', help='The directory to clone the repo into')
@click.option('--commit_hash', help='The commit hash to kickoff')
@click.option('--task_id', help='The task id to kickoff')
@click.option('--unix_start', help='The unix start time of the task')
def kickoff_cli(team_id, repo_dir, commit_hash, task_id, unix_start):
    kickoff(team_id, repo_dir, commit_hash, task_id, unix_start)