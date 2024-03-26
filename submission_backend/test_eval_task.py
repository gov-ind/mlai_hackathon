from datetime import datetime, timezone
import uuid
import os
import json
import docker
import pytest
import shutil

from eval_task import generate_output, full_eval
from pytestutils import *
from task_manager import *

@pytest.fixture(scope='session')
def docker_image():
    submission_dir = "submission_backend/cruft/bot"
    # Delete the directory if it exists, or else Unix will write the `bot` directory
    # into `{submission_dir}/bot`.
    if os.path.exists(submission_dir):
        shutil.rmtree(submission_dir)
    os.system(f"cp -r bot {submission_dir}")
    with open("submission_backend/cruft/bot/config.json", "r") as f:
        config = json.load(f)
    
    config['policy']['class_name'] = "HistoricalPricePolicy"

    with open(f"{submission_dir}/config.json", "w") as f:
        json.dump(config, f)

    client = docker.from_env()
    
    docker_image_tag = str(uuid.uuid4())
    print('### Building image')
    result = client.images.build(path=submission_dir, tag=docker_image_tag, quiet=False)
    print(result[0], type(result[0]))
    print(dir(result[0]))

    for item in result[1]:
        print(item)

    yield docker_image_tag

    client.images.remove(docker_image_tag)
    os.system("rm -r submission_backend/cruft/bot")


@pytest.fixture(scope='session')
def broken_docker_image():
    submission_dir = "submission_backend/cruft/bot"
    # Delete the directory if it exists, or else Unix will write the `bot` directory
    # into `{submission_dir}/bot`.
    if os.path.exists(submission_dir):
        shutil.rmtree(submission_dir)
    os.system(f"cp -r bot {submission_dir}")
    with open("submission_backend/cruft/bot/config.json", "r") as f:
        config = json.load(f)
    
    config['policy']['class_name'] = "POLICY THAT DOES NOT EXIST!!!"

    with open(f"{submission_dir}/config.json", "w") as f:
        json.dump(config, f)

    client = docker.from_env()
    
    docker_image_tag = str(uuid.uuid4())
    print('### Building image')
    result = client.images.build(path=submission_dir, tag=docker_image_tag, quiet=False)
    print(result[0], type(result[0]))
    print(dir(result[0]))

    for item in result[1]:
        print(item)

    yield docker_image_tag

    client.images.remove(docker_image_tag)
    os.system("rm -r submission_backend/cruft/bot")

def test_eval_task_generates_output(docker_image):
    current_working_directory = os.getcwd() 
    output_directory = os.path.join(current_working_directory, "submission_backend", "output") # must be an absolute path or else docker does not let us use it as a volume

    output = generate_output(0, 0, 999999999999999, output_directory, docker_image)
    
    output['main_trial'] = output['trials'][output['main_trial_idx']]
    assert len(output['main_trial']['actions']) == 6335

def test_eval_task_generates_bounded_output(docker_image):
    current_working_directory = os.getcwd() 
    output_directory = os.path.join(current_working_directory, "submission_backend", "output") # must be an absolute path or else docker does not let us use it as a volume

    start_time = datetime(2023, 4, 15, 0, 5, tzinfo=timezone.utc).timestamp()
    end_time = datetime(2023, 4, 16, tzinfo=timezone.utc).timestamp() 
    output = generate_output(start_time, start_time, end_time, output_directory, docker_image)
    
    output['main_trial'] = output['trials'][output['main_trial_idx']]
    assert len(output['main_trial']['actions']) == 287


def test_eval_task_generates_bounded_offset_output(docker_image):
    current_working_directory = os.getcwd() 
    output_directory = os.path.join(current_working_directory, "submission_backend", "output") # must be an absolute path or else docker does not let us use it as a volume

    data_start_time = datetime(2023, 4, 15, 0, 5, tzinfo=timezone.utc).timestamp()
    start_time = int(datetime(2023, 4, 16, tzinfo=timezone.utc).timestamp())
    end_time = datetime(2023, 4, 17, tzinfo=timezone.utc).timestamp() 
    output = generate_output(data_start_time, start_time, end_time, output_directory, docker_image)
    
    output['main_trial'] = output['trials'][output['main_trial_idx']]
    assert len(output['main_trial']['actions']) == 288


def test_eval_saves_to_db(docker_image, db_client):
    start_time = datetime(2023, 4, 15, 0, 5, tzinfo=timezone.utc).timestamp()
    batch_end_time = datetime(2023, 4, 16, tzinfo=timezone.utc).timestamp() 

    with open('.credentials.json') as f:
        credentials = json.load(f)
    database = Database(credentials['AWS_ACCESS_KEY_ID'], credentials['AWS_SECRET_ACCESS_KEY'])
    tm = TaskManager(database)
    task_id = tm.database.create_task("smol bean command pls ignore uwu")
    all_tasks = tm.database.get_tasks()
    assert len(all_tasks) == 1

    team_name = "kevin rudds team"
    submissions = db_client.load_all_submissions(team_name)
    assert len(submissions) == 0

    current_working_directory = os.getcwd()
    data_dir = os.path.join(current_working_directory, "submission_backend", "output")
    full_eval(start_time, start_time, batch_end_time, data_dir, docker_image, team_name, "as5851234t32gre", task_id)

    task= tm.database.get_task(task_id)
    assert task['state_'] == 'success'
    
    submissions = db_client.load_all_submissions(team_name)
    assert len(submissions[0]['main_trial']['profits']) == 287
    assert len(submissions[0]['main_trial']['socs']) == 287
    assert len(submissions) == 1

    batch_start_time = datetime(2023, 4, 16, tzinfo=timezone.utc).timestamp()
    batch_end_time = datetime(2023, 4, 17, tzinfo=timezone.utc).timestamp()

    task2_id = tm.database.create_task("(☉_☉)")
    all_tasks = tm.database.get_tasks()
    assert len(all_tasks) == 2

    full_eval(start_time, batch_start_time, batch_end_time, data_dir, docker_image, team_name, "as5851234t32gre", task2_id)

    task2 = tm.database.get_task(task2_id)
    assert task2['state_'] == 'success'

    submissions = db_client.load_all_submissions(team_name)
    assert len(submissions) == 1
    assert len(submissions[0]['main_trial']['profits']) == 575
    assert len(submissions[0]['main_trial']['socs']) == 575

    for task in all_tasks:
        tm.database.delete_task(task['id'])
        tm.database.delete_task(task2['id'])

    db_client.delete_submission(team_name, "as5851234t32gre")
    submissions = db_client.load_all_submissions(team_name)
    assert len(submissions) == 0

def test_eval_task_raises_an_error_for_docker_error(broken_docker_image, db_client):
    start_time = datetime(2023, 4, 15, 0, 5, tzinfo=timezone.utc).timestamp()
    end_time = datetime(2023, 4, 16, tzinfo=timezone.utc).timestamp() 

    with open('.credentials.json') as f:
        credentials = json.load(f)
    database = Database(credentials['AWS_ACCESS_KEY_ID'], credentials['AWS_SECRET_ACCESS_KEY'])
    tm = TaskManager(database)

    task_id = tm.database.create_task("smol bean command pls ignore uwu")

    team_name = "dumb idiots"
    current_working_directory = os.getcwd()
    data_dir = os.path.join(current_working_directory, "submission_backend", "output")
    full_eval(start_time, start_time, end_time, data_dir, broken_docker_image, team_name, "as5851234t32affddafse", task_id)

    loaded_task = tm.database.get_task(task_id)
    assert loaded_task['state_'] == 'error'

    tm.database.delete_task(task_id)    

def test_eval_task_raises_an_error_for_system_error(docker_image, db_client):
    start_time = datetime(2023, 4, 15, 0, 5, tzinfo=timezone.utc).timestamp()
    end_time = datetime(2023, 4, 16, tzinfo=timezone.utc).timestamp() 

    with open('.credentials.json') as f:
        credentials = json.load(f)
    database = Database(credentials['AWS_ACCESS_KEY_ID'], credentials['AWS_SECRET_ACCESS_KEY'])
    tm = TaskManager(database)

    task_id = tm.database.create_task("smol bean command pls ignore uwu")

    current_working_directory = os.getcwd()
    data_dir = os.path.join(current_working_directory, "submission_backend", "output")
    full_eval(start_time, start_time, end_time, data_dir, docker_image, 80085, "as5851234t32affddafse", task_id)

    loaded_task = tm.database.get_task(task_id)
    assert loaded_task['state_'] == 'error'    

    tm.database.delete_task(task_id)
