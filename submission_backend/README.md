## Run energy trading evaluation back-end for development testing

The back-end uses Docker to build a Docker image containing the Python
run-time environment and the participant team submission code (algorithm)
... and then runs a Docker container using that Docker image.

This produces a results file called `submisison_backend/cruft/output.json`,
which is in the form of the Submission Schema in the next section.

From the top-level directory, run the following commands ...

    python3 -m venv venv               # create Python virtual environment
    source venv/bin/activate
    cd submission_backend && pip install .
    python submission_backend/dock.py  # output: "submission_backend/cruft/output.json"

## Try the TaskManager prototype

TaskManager is a work-in-progress prototype, which is effectively the engine of
the proposed conceptual system design (see below).  The current implementation
provides basic Task management via the CLI and uses the AWS DynamoDB for
persistence.

Assuming that the Python virtual environment is already created and activated,
then the following commands provide an insight into the current state-of-play.

#### Set-up for AWS hosted DynamoDB

    cp -a example.credentials.json .credentials.json
    vi .credentials.json  # AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY

*Note: `.gitignore` prevents `.credentials.json` from being added to Git*

*Note: `TaskManager` prepends your `username` to the DynamoDB table names to
avoid everyone stepping on each other's toes*

#### Alternate set-up for locally hosted DynamoDB

    docker-compose up   # Local DynamoDB instance for development testing, you may now interact with the database inside the docker container in another shell.

#### Task and Timer create, run, list, update and delete commands

This first command "check" runs some basic code and database checks.
If required, this creates the database tables, creates some Tasks,
then tries deleting, reading and updating the Tasks.
You can run it multiple times and more Tasks are created and added to the list.

*Note: Currently there is a noticeable delay in the middle of this test.
Cause is yet to be determined and fixed*

    ./task_manager.py check             # test database (developers only)

##### Create a Task to run a given shell command

    ./task_manager.py create <COMMAND>
    ./task_manager.py create "echo Hello"  # built-in "echo" command
    ./task_manager.py create "sleep 5"     # built-in "sleep" command
    ./task_manager.py create date          # run an external shell command
    ./task_manager.py create ./test.py     # run a Python script

Commands with parameters must be delimited by quotes, e.g "a b c"

    ./task_manager.py create "./test.py parameter_1 parameter_2"

##### Run the TaskManager, which will process all Timers and pending Tasks

    ./task_manager.py list  # before
    ./task_manager.py run --sleep 5
    # Interupt via Control-C once Tasks are processed
    ./task_manager.py list  # after

For Timers to run on time ... the sleep time parameter should be
the same (or less than) the fastest Timer.

##### Create a Timer to run a given Task command

    ./task_manager.py timer --help                       # show CRONTAB format
    ./task_manager.py timer <COMMAND> <CRONTAB>
    ./task_manager.py timer "echo S15" "0/15 * * * * *"  # every 15 seconds
    ./task_manager.py timer "echo M01" "* 0/1 * * * *"   # every  1 minute
    ./task_manager.py list
    ./task_manager.py run --sleep 5
    # Interupt via Control-C after a few minutes
    ./task_manager.py list

The CRONTAB argument format (delimited by quotes) is ...

    .------------------------ second       (0 - 59)
    |   .-------------------- minute       (0 - 59)
    |   |   .---------------- hour         (0 - 23)
    |   |   |   .------------ day of month (1 - 31)
    |   |   |   |   .-------- month        (1 - 12)
    |   |   |   |   |   .---- day of week  (1 - 7): Monday = 1
    |   |   |   |   |   |
    *   *   *   *   *   *     "*" is a wildcard, i.e matches any value.

    0   0   0   *   *   *     "n" matches exact value, e.g just at midnight
    0   *   0/4 *   *   *     "Absolute time/Relative time", e.g every 4 hours
    *   0/1 *   *   *   *     "Absolute time/Relative time", e.g every minute

Note: Currently only the Crontab "Absolute time/Relative time" format is supported.

##### Delete a specified Task id.

*Note: This is not recommended at the moment, except for developers*

    ./task_manager.py delete <TASK_ID>  # warning: may cause problems

##### Delete all the database tables for the current `username`.

*Note: Take special care to never destroy the production database*

    ./task_manager.py destroy

##### List Tasks with various ways of filtering the output

    ./task_manager.py list
    ./task_manager.py list --all   # show all Task fields
    ./task_manager.py list --field command <COMMAND>
    ./task_manager.py list --field id <TASK_ID>
    ./task_manager.py list --field id <TASK_ID> --all  # this is handy
    ./task_manager.py list --field state <pending|running|success|error>

##### Update Task field values, such as `command`, `diagnostic`, `state`

    ./task_manager.py update <TASK_ID> <FIELD_NAME> <FIELD_VALUE>

#### Demonstrate the whole system running using some mock Tasks

##### Run a single mock Task_3

This simulates running a single team submission,

    ./task_manager.py create "./mock_task_run_submission.py teamA"
    ./task_manager.py list  # before
    ./task_manager.py run --sleep 1
    # Interupt via Control-C once the Task is processed
    ./task_manager.py list  # after

##### Run a chain of two mock Tasks: Task_2 --> Task_3

This simulates running all the team submissions.

The first Task_2 actually creates three Task_3s with different team names.

    ./task_manager.py create ./mock_task_run_submissions.py
    ./task_manager.py list  # before
    ./task_manager.py run --sleep 1
    # Interupt via Control-C once all 4 Tasks are processed
    ./task_manager.py list  # after

##### Run a chain of three mock Tasks: Task_1 --> Task_2 --> Task_3

This simulates getting the latest live energy datapoints, then running all the
team's latest submissions using that those energy datapoints.

    ./task_manager.py create ./mock_task_get_data.py
    ./task_manager.py list  # before
    ./task_manager.py run --sleep 1
    # Interupt via Control-C once all 5 Tasks are processed
    ./task_manager.py list  # after

##### Run a Timer regularly invoking a chain of three mock Tasks

This simulates polling for latest live energy datapoints every 10 seconds,
then running all the team's latest submissions accordingly.

    ./task_manager.py timer ./mock_task_get_data.py "0/10 * * * * *"
    ./task_manager.py list  # before
    ./task_manager.py run --sleep 1
    # Interupt via Control-C once you are bored :)
    ./task_manager.py list  # after

#### Clean-up and shutdown local DynamoDB

    ./task_manager.py destroy
    docker-compose down  # Local DynamoDB instance for development testing

## System conceptual design

A modular approach is proposed, which enables (1) flexibility and expand-ability (especially for different deployment choices) and (2) easier contribution by multiple team members.  A TaskManager, via a Task queue, coordinates the execution of Tasks via the modular TaskHandlers.  Events cause new Tasks to be placed into the TaskManager Task queue.  An initial simplification is that all persistent data is stored in the DynamoDB.

![System conceptual design](../design/system_conceptual_design.png)

- **TaskManager** is a web server providing a web based TaskManager UI (primarily for testing and diagnosis).  A HTTP API supports new Task creation for Event triggers.  TaskHandlers are independent Unix processes

- **Tasks** or TaskHandlers ...
    - **Update AEMO data points**: Accesses OpenNem and populates the DynamoDB
    - **Build Team Docker image**: Accesses the Team GitHub repository and builds an updated Docker image for later use
    - **Run Team Docker image**: Performs evaluation using specified AEMO data points, e.g either live or from a specified data range (historical)
    - **Update Leaderboard**: Consolidates new Team evaluation scores and updates the Leaderboard accordingly

- **Leaderboard web based UI**: Served as static HTML/JS/CSS content and access the DynamoDB directly

####Proposed Tasks

- Time (event) based Tasks, which may initiate a chain of more Tasks

    - T1) Poll for fetching latest energy datapoints and putting them in the "energy_datapoints" Database Table --> For all teams create Task T4 (multiple)

    - T2) Poll for checking team GitHub repositories for new submissions (since the last submission) --> For teams with new submission create Task T4 (multiple)

- Tasks that are created by other tasks

    - T3) Build Docker Image --> Create Task T4

    - T4) Run Team Docker Container --> Create Task T5

    - T5) Update Team's score --> Create Task T6

    - T6) Update leaderboard

#### Design and Implementation Notes

In the current design and implementation ... there is only a single TaskManager instance (Unix process), which processes the pending Tasks in-order of creation ... one at a time ... one after the other.  Timers (inspired by `crontab`) can create Tasks periodically or at specified times.

This is to keep the concurrency issues simple and easy to reason about.  
Note: The current design can be extended for concurrent Tasks, if we need more parallelism.

When the TaskManager causes a pending Task to run ...

        state: pending --> running --> success or error + diagnostic

... then the Task is started via a `command`, which includes `parameters`.  
Conceptually, this is just like a Unix shell command line ...

        command parameter_1 parameter_2 ... &

- The Task command including the parameters are stored in the DynamoDB Task table ... with a unique task_id

Tasks may ...

- Run outside of a Docker Container ... all of our code ... that may interact directly with the DynamoDB (with careful, coordinated design, especially if updating)

- Run inside of a Docker Container ... all the team’s code ... of course, they must never access the DynamoDB directly (they won’t have security credentials)

- Perform work using any approach, e.g shell command or script, Python (preferred) or some other language (if really needed)

- Finish with an `exit code (int8)`, where 0 (zero) means `success` and non-zero means `error`

- Create another Task ... this is the main driver for the system design.  Finishing one Task ... causes another Task to run ... until the overall goal is reached

Tasks can create other Tasks ... via `task_manager.py:create_task(command)`.
This does not mean that every Task has a TaskManager instance.  What happens is that the `create_task(command)` uses a Database client connection instance to update the DynamoDB Task table.  
Note: The `create_task()` function has been deliberately designed and implemented to be concurrency safe.
Whenever multiple things (running Task, command line tool, timer, etc) try to create a new Task, then a mutual exclusion "lock" prevents two Tasks with the same task_id being created.

All other Task database operations are not concurrency safe.  The current protection mechanism is that the TaskManager only runs a single Task at a time.  This was a deliberate design decision to get us underway quickly and simply ... and can be changed in the future (especially after we know what we truly need).

Using TaskHandlers as Unix processes and storing all persistent data in DynamoDB should simplify trying different deployment approaches, e.g one server (initially) versus multiple servers (given specific performance / cost goals)

Python DynamoDB code should be consolidated into a single source file (rather than being spread throughout the source code) for easier maintenance and checking against the equivalent JavaScript DynamoDB code

If we choose to *poll* (pull) the Team participant's GitHub repositories (instead of using a "push" GitHub action / web-hook), then that can be accomplished by setting up a regular "time" Event trigger that causes a "Poll Team GitHub repository" TaskHandler to run through the list of Team participants

#### Operational hints and tips

To avoid AWS DynamoDB "production" instance mishaps (or collisions between developers) during development, either ...

- Run a local copy of DynamoDB on your laptop

        cd submission_backend
        docker-compose up  # Local DynamoDB instance for development testing
        export DB_URL="--endpoint-url http://localhost:8000"

- Inside `task_manager.py`

        DB_URL = "http://localhost:8000"

... or ...

- When using the AWS DynamoDB "production" instance ... then prefix all the development Tables with your $USERNAME  

        # During development "DB_PREFIX" avoids everyone stepping on each other's toes
        DB_PREFIX = os.environ.get("USER", os.environ.get("USERNAME"))  # works on Linux, Mac OS X and Windows !
        DB_DATAPOINTS_TABLE_NAME = f"{DB_PREFIX}_datapoints"
        DB_TASKS_TABLE_NAME = f"{DB_PREFIX}_tasks"

- For the actual, real production DynamoDB, use the prefix `"energy"` instead of your `$USERNAME`

#### Future design and implementation thoughts

- Determine an automated approach to **limiting resource usage**, e.g CPU time,
  ML model size, system memory.  This would stop a Team Docker container from
  exceeding reasonable limits and either blocking other Teams or consuming all
  our AWS credits.  If a Team's Docker container does exceeds limits, then they
  should receive a notification that informs them to ask ML/A.I AUS whether it
  is possible to adjust limits on a case-by-case basis.

## Submission Schema

The schema for participant data saved to the public dynamodb database is given below.

```json
{
    "main_trial_idx": 0.0,
    "error_traceback": null,
    "main_trial": {
        "profits": [
            -7.979027700261019,
            3.5329587136597684,
        ],
        "socs": [
            53.75,
            49.120370370370374,
            52.870370370370374,
        ],
        "market_prices": [
            34.14524892893011,
            23.603033351187605,
        ],
        "timestamps": [
            1704067200, # 2024-01-01 00:00:00
            1704067500, # 2024-01-01 00:05:00
        ],
        "actions": [
            50.0,
            -50.0,
        ],
    },
    "status": "success",
    "class_name": "RandomPolicy",
    "score": 3.5329587136597684,
    "submitted_at": 1709940984995.0,
    "num_runs": 100.0,
    "parameters": {},
    "team_name": "scream-team",
    "team_id": 107, # team ids range from 100-200
    "city": "SYD", 
    "error": null,
    "git_commit_hash": "098fffa0-bf29-45ef-81c8-b10d72aa62e2"
}
```

An example database in JSON format is given in `data/example_submission_database.json`.

In addition more data will be saved to the private database. The main differnce between the public and the private database is that it may contain an additional `"trials"` key which may be an arrray containing tens or hundreds of trials in the exact same format as `"main_trial"`. This will likely be saved as individual JSON files each named `TEAM_NAME-COMMIT_HASH` since dynamodb can only handle 400k of data per item and 100 trials will be far larger than this amount.

## Task Data Format

This is the basic format which all tasks will contain, keeping in mind that more keys may be added and that no strict rules exist at all for "parameters". One requirement is that we be able to show teams the tasks which pertain to their submissions so they can quickly tell if their submissions actually worked.

```json
{
        "task": "task",  # this is the primary key for dynamodb, it is always task
        "id": 1823,
        "command": "python evlauate.py --data file.json",
        "created_at": 1704067200,
        "diagnostic": "",
        "state_": "pending", # error, success, running, pending timer
        "task": "submission-kickoff", # submission-kickoff, timer-data-polling, timer-repo-polling, evaluation, data-polling, repo-polling
        "team_name": "shalmaneser III and the bois", # optional!
        "team_id": 103, # optional!
        "git_commit_hash": "d7hbt37qgfeiwyoiu", # optional!
        ...
},
{
        "task":"task" # this is the primary key for dynamodb, it is always task
        "id": 7, # secondary key
        "command": "python poll_repos.py",
        "created_at": 1704068200,
        "diagnostic": "",
        "state_": "running", # error, success, running, pending
        "task": "repo-polling", # submission-kickoff, timer-data-polling, timer-repo-polling, evaluation, data-polling, repo-polling
        ...
}
...

```

NOTE: the frontend will need to query the "team_id" on the backend so we will need to set up an index on this key, which will solve the issue. We may also set one up on CreatedAt.

