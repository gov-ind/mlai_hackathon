from task_manager import *
from pytestutils import *

def test_tm_create_task_with_parameters(tm_client: TaskManager):
    task_id = tm_client.database.create_task("cowsay 'great scott'")

    tasks = tm_client.database.get_tasks()
    assert len(tasks) == 1

    cowsay_task = tasks[-1]
    assert int(cowsay_task["id"]) == task_id

    tm_client.database.delete_task(task_id)
    tasks = tm_client.database.get_tasks()
    assert len(tasks) == 0

def test_updates_task_with_more_than_one_key(tm_client: TaskManager):
    task_id = tm_client.database.create_task("cowsay 'great scott'")

    tm_client.database.update_task(str(task_id), {"state_": "success", "diagnostic": "this is a test"})

    tasks = tm_client.database.get_tasks()
    assert tasks[-1]["state_"] == "success"
    assert tasks[-1]["diagnostic"] == "this is a test"

    tm_client.database.delete_task(task_id)
    tasks = tm_client.database.get_tasks()
    assert len(tasks) == 0

def test_updates_task(tm_client: TaskManager):
    task_id = tm_client.database.create_task("cowsay 'great scott'")

    tm_client.database.update_task(str(task_id), {"state_": "success"})

    tasks = tm_client.database.get_tasks()
    assert tasks[-1]["state_"] == "success"

    tm_client.database.delete_task(task_id)
    tasks = tm_client.database.get_tasks()
    assert len(tasks) == 0

def test_tm_create_task(tm_client: TaskManager):
    tasks = tm_client.database.get_tasks()

    assert len(tasks) == 0