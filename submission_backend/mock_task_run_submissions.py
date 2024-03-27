#!/usr/bin/env python3
#
# Description
# ~~~~~~~~~~~
# Pretends to get the team list, then creates Run Submission Task for each team
#
# Usage
# ~~~~~
# This Task can be tested by just running it once
#
# ./task_manager.py create "./mock_task_run_submissions.py"
# ./task_manager.py run -s 5

import time

from task_manager import CONFIGURATION_PATHNAME, Database, load_configuration

def run_submissions(database):
    print("---- Mock run_submissions: started")
    for team_name in ["TeamA", "TeamB", "TeamC"]:
        command = f"./mock_task_run_submission.py {team_name}"
        task_id = database.create_task(command)
    print("---- Mock run_submissions: stopped")

if __name__ == "__main__":
    aws_access_key_id, aws_secret_access_key = load_configuration(
        CONFIGURATION_PATHNAME)
    database = Database(aws_access_key_id, aws_secret_access_key)
    run_submissions(database)

#---------------------------------------------------------------------------- #
