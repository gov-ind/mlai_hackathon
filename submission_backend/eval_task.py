import uuid
import click
import json
import traceback
import docker
import os
import pandas as pd
from energy_db import EnergyDB
from leaderboard_db import LeaderboardDBClient
from team_db import TeamDB
from task_manager import *
from task_manager_utils import tm_raise_error

def full_eval(unix_start:int, batch_unix_end:int, data_dir:str, docker_image_tag:str, team_id: int, commit_sha:str, task_id:int):
    try:
        with open('.credentials.json') as f:
            credentials = json.load(f)
        task_db = Database(credentials['AWS_ACCESS_KEY_ID'], credentials['AWS_SECRET_ACCESS_KEY'])
        tm = TaskManager(task_db)
        tm.database.update_task(str(task_id), {"state_": 'running'})

        db_client = LeaderboardDBClient(credentials['AWS_ACCESS_KEY_ID'], credentials['AWS_SECRET_ACCESS_KEY'])
        submission = db_client.load_latest_submission(
            team_id=team_id,
            commit_hash=commit_sha
        )    
        if submission is None:
            first_timestamp_in_batch = unix_start
        else:
            first_timestamp_in_batch = submission['main_trial']['timestamps'][-1] + 300

        team_db = TeamDB(credentials['AWS_ACCESS_KEY_ID'], credentials['AWS_SECRET_ACCESS_KEY'])
        team = team_db.get_team(team_id)
        if team is None:
            raise ValueError(f"Team {team_id} does not exist")
    except Exception as e:
        tm_raise_error(tm, task_id, f'Error loading team/submission, {e}')
        return

    try:
        output = generate_output(unix_start, first_timestamp_in_batch, batch_unix_end, data_dir, docker_image_tag)
    except Exception as e:
        print('ERROR', e)
        trace = traceback.format_exc() 
        tm_raise_error(tm, task_id, f'Error running docker image, {e}, traceback: {trace}')
        return
    
    try:

        submission = {
            'team_name': team['team_name'],
            'team_id': team_id,
            'git_commit_hash': commit_sha,
            'score': 0,
            'error': None,
            'error_traceback': None,
        }

        for k, v in output.items():
            submission[k] = v

        submission['main_trial'] = submission['trials'][submission['main_trial_idx']]
        del submission['trials']

        db_client.upsert_submission(submission)
        tm.database.update_task(str(task_id), {'state_': 'success'})
    except Exception as e:
        trace = traceback.format_exc() 
        print('ERROR', e, trace)
        tm_raise_error(tm, task_id, f'Error submitting to leaderboard, {e}, traceback: {trace}')
    
def generate_output(unix_start:int, unix_batch_start:int, batch_unix_end:int, data_dir:str, docker_image_tag:str):
    edb = EnergyDB()
    data = edb.get_data(unix_start, batch_unix_end)

    if unix_batch_start not in data['timestamp'].values:
        if unix_batch_start > edb.earliest_timestamp():
            raise ValueError(f"Start time {unix_batch_start} is after the earliest timestamp {edb.earliest_timestamp()} in the data but not actually in the data")
        else:
            start_index = 0
    else:
        start_index = data[data['timestamp'] == unix_batch_start].index[0]

    input_file = os.path.join(data_dir, f'{uuid.uuid4()}.csv')
    data.to_csv(input_file)

    output_file = os.path.join(data_dir, f'{uuid.uuid4()}.json')
    client = docker.from_env()
    
    container = client.containers.run(
        docker_image_tag, 
        command=f"python bot/evaluate.py --output_file {output_file} --data {input_file} --present_index {start_index}", 
        volumes={data_dir: {'bind': data_dir, 'mode': 'rw'}},
        detach=True,
        network_mode="none",
    )

    for line in container.logs(stream=True):
        print(line.strip())

    container.stop()
    container.remove()

    os.remove(input_file)

    with open(output_file, 'r') as f:
        output_data = json.load(f)

    os.remove(output_file)
    return output_data

@click.command()
@click.option('--unix_start', type=int, help='Start Unix timestamp.')
@click.option('--batch_unix_end', type=int, help='End Unix timestamp.')
@click.option('--data_dir', type=str, help='Directory for data files.')
@click.option('--docker_image_tag', type=str, help='Docker image tag.')
@click.option('--commit_hash', type=str, help='Commit SHA.')
@click.option('--team_id', type=int, help='Team ID.')
@click.option('--task_id', type=int, help='Task ID.')
def full_eval_cli(unix_start:int, batch_unix_end:int, data_dir:str, docker_image_tag:str, team_id:int, commit_hash:str, task_id:int):
    full_eval(unix_start, batch_unix_end, data_dir, docker_image_tag, team_id, commit_hash, task_id)

if __name__ == '__main__':
    full_eval_cli()