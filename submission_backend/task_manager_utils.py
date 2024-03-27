from task_manager import *

def tm_raise_error(tm: TaskManager, task_id, error_message):
    tm.database.update_task(str(task_id), {
        'state_': 'error',
        'diagnostic': error_message
    })
