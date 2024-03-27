#!/usr/bin/env python3
#
# Description
# ~~~~~~~~~~~
# Pretends to get data, then creates a Run Submissions Task
#
# Usage
# ~~~~~
# This Task is intended to be created (repeatedly) by a Timer
#
# ./task_manager.py timer "./mock_task_get_data.py" "* 0/4 * * * *"
# ./task_manager list
# ./task_manager.py run -s 5
# ./task_manager list
#
# This Task can be tested by just running it once
#
# ./task_manager.py create "./mock_task_get_data.py"
# ./task_manager.py run -s 5

import time

from task_manager import CONFIGURATION_PATHNAME, Database, load_configuration

def get_data(database):
    print("---- Mock get data: started")
    # Get data and store in database

    command = "./mock_task_run_submissions.py"
    task_id = database.create_task(command)
    print("---- Mock get data: stopped")

if __name__ == "__main__":
    aws_access_key_id, aws_secret_access_key = load_configuration(
        CONFIGURATION_PATHNAME)
    database = Database(aws_access_key_id, aws_secret_access_key)
    get_data(database)

#---------------------------------------------------------------------------- #
