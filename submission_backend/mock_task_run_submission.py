#!/usr/bin/env python3
#
# Description
# ~~~~~~~~~~~
# Pretends to run a team submission
#
# Usage
# ~~~~~
# This Task can be tested by just running it once
#
# ./task_manager.py create "./mock_task_run_submission.py team_name"
# ./task_manager.py run -s 5

import sys
import time

from task_manager import CONFIGURATION_PATHNAME, Database, load_configuration

def run_submission(database, team_name):
    print(f"---- Mock run_submission for team {team_name}: started")
    print(f"---- Mock run_submission for team {team_name}: stopped")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('#### ERROR: mock_task_run_submission.py missing "team_name" argument')
        sys.exit(1)
    team_name = sys.argv[1]

    aws_access_key_id, aws_secret_access_key = load_configuration(
        CONFIGURATION_PATHNAME)
    database = Database(aws_access_key_id, aws_secret_access_key)
    run_submission(database, team_name)

#---------------------------------------------------------------------------- #
