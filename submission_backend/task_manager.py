#!/usr/bin/env python3
#
# Usage: AWS DynamoDB set-up
# ==========================
#
# Usage: Local DynamoDB set-up
# ============================
# docker-compose up  # Local DynamoDB instance for development testing
# export DB_URL="--endpoint-url http://localhost:8000"
#
# Usage: Task create, list, update, delete commands
# -------------------------------------------------
# ./task_manager check             # test database (developers only)
# ./task_manager create <COMMAND>
# ./task_manager delete <TASK_ID>  # warning: may cause problems
# ./task_manager destroy           # don't destroy the production database
# ./task_manager list
# ./task_manager list --all        # show all Task fields
# ./task_manager list --field command <COMMAND>
# ./task_manager list --field id <TASK_ID>
# ./task_manager list --field state <pending|running|success|error>
# ./task_manager update <TASK_ID> <FIELD_NAME> <FIELD_VALUE>
#
# Usage: AWS CLI
# --------------
# aws dynamodb $DB_URL list-tables
# aws dynamodb $DB_URL describe-table --table-name energy_tasks
# aws dynamodb $DB_URL get-item --table-name energy_tasks --consistent-read \
# aws dynamodb $DB_URL query --table-name energy_tasks \
#     --key-condition-expression "task = :name" \
#     --expression-attribute-values '{":name":{"S":"task"}}'
# aws dynamodb $DB_URL delete-table   --table-name energy_tasks
#
# Usage: Clean-up and shutdown local DynamoDB
# -------------------------------------------
# ./task_manager.py destroy
# docker-compose down  # Local DynamoDB instance for development testing
#
# Resources
# ~~~~~~~~~
# - https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
# - https://boto3.amazonaws.com/v1/documentation/api/latest/guide/dynamodb.html
# - https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#configuring-credentials
# - https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.DownloadingAndRunning.html
# - https://aws.amazon.com/blogs/database/implement-auto-increment-with-amazon-dynamodb
#
# To Do
# ~~~~~
# * FIX: Improve DynamoDB Tasks table schema partition and sort keys
#   - Run performance tests before and after improving partition and sort keys
#
# * FIX: create_unique_item() problem with gaps in the task ids
# * Consider Tasks table: "id" sort key type ... integer or string ?
#
# - FIX: Capture database errors (avoid messy stack traceback)
#   - Database table missing: table.query() and table.scan()
#
# - Review Slack conversation with Louka: trading submission detailed design
#
# - Implement logger with date/time
# - Implement performance measurement
#
# - Refactor "class Database" into separate source code file
# - Create "class Task"
#
# * Implement task_manager import and export commands
#
# - Create AWS Boto3 configuration data structure
#   - Include optional local Boto3 endpoint
#
# - TaskHandler template and example
#   - Use Service Provider Interface (SPI) ?
#   - Process.run()
#   - Update DynamoDB
#   - Run Docker container
#   - Set CPU and memory limits
#
# - Design and implement Tasks on DynamoDB ...
#   - Create Task via internal timer Tasks
#   - Create Task from external event (HTTP)
#
# - Design and implement Teams on DynamoDB
#   - Submission runs: created_at, run_at, run_time, state_ ?
#
# - Web server <--> Web UI
#   - Task queue CRUD
#   - Event --> pending Task

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError as BotocoreClientError
import click
from datetime import date, datetime, timezone
from flask import Flask
import json
import os
from pprint import pprint
import subprocess
import time

RUN_LOOP_SLEEP_TIME = 60  # seconds ... can be overridden on the command line

CONFIGURATION_PATHNAME = ".credentials.json"
# DB_URL = None                   # use AWS hosted DynamoDB instance
DB_URL = "http://localhost:8000"  # use local DynamoDB instance

# During development "DB_PREFIX" avoids everyone stepping on each other's toes
DB_PREFIX = os.environ.get("USER", os.environ.get("USERNAME"))
DB_DATAPOINTS_TABLE_NAME = f"{DB_PREFIX}_datapoints"  # "green-battery-hack"
DB_TASKS_TABLE_NAME = f"{DB_PREFIX}_tasks"

DB_TABLE_SCHEMAS = {
    DB_DATAPOINTS_TABLE_NAME: ("commit_id", "team", 5, 5),
    DB_TASKS_TABLE_NAME:      ("task",      "id",   1, 1)
}

# Note: DynamoDB has the "state" reserved word, so "state_" is used instead
# Note: "created_at" and "run_at" are when Task creation and execution occurred

DB_TASK_FIELD_NAMES = [  # mutable task fields, i.e not task keys
    "command", "created_at", "crontab", "diagnostic", "run_at", "state_"
]

# --------------------------------------------------------------------------- #
# Table: energy_datapoints
#   AttributeName: commit_id, AttributeType: S, KeyType: HASH
#   AttributeName: team,      AttributeType: S, KeyType: RANGE
#
# Table: energy_tasks
#   AttributeName: task,       AttributeType: S, KeyType: HASH
#   AttributeName: id,         AttributeType: S, KeyType: RANGE
#   AttributeName: state_,     AttributeType: S, pending running success error
#   AttributeName: command,    AttributeType: S, Command with parameters
#   AttributeName: diagnostic, AttributeType: S, "Message for success or error"
#   AttributeName: created_at, AttributeType: S, datetime.utcnow().isoformat()
#   AttributeName: run_at,     AttributeType: S, datetime.utcnow().isoformat()

class Database():
    def __init__(self, aws_access_key_id, aws_secret_access_key):
        self.boto3_session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name="ap-southeast-2"
        )

        db_args = {"service_name": "dynamodb"}
        if DB_URL:
            db_args["endpoint_url"] = DB_URL
    #   self.db_client = self.boto3_session.client(**db_args)      # low-level
        self.db_resource = self.boto3_session.resource(**db_args)  # high-level
        self.delete_task_warning = True

        self.create_tables()
        self.datapoints_table = self.get_table(DB_DATAPOINTS_TABLE_NAME)
        self.tasks_table = self.get_table(DB_TASKS_TABLE_NAME)

# Database tables functions ................................................. #

    def create_table(self, table_name, table_schema):
        partition_key_name, sort_key_name,  \
            read_capacity_units, write_capacity_units = table_schema

        key_schema = [{"AttributeName": partition_key_name, "KeyType": "HASH"}]
        if sort_key_name:
            key_schema.append(
                {"AttributeName": sort_key_name, "KeyType": "RANGE"})

        attr_def = [{"AttributeName": partition_key_name, "AttributeType": "S"}]
        if sort_key_name:
            attr_def.append(
                {"AttributeName": sort_key_name, "AttributeType": "S"})

        table = self.db_resource.create_table(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attr_def,
            ProvisionedThroughput={
                "ReadCapacityUnits": read_capacity_units,
                "WriteCapacityUnits": write_capacity_units
            }
        )
        table.wait_until_exists()
        return table

    def create_tables(self):
        for table_name, table_schema in DB_TABLE_SCHEMAS.items():
            table = self.get_table(table_name)
            if not table:
                table = self.create_table(table_name, table_schema)

    """
    def describe_table(self, table_name):
        table_description = self.db_client.describe_table(TableName=table_name)
        pprint(table_description)
    """

    def destroy_tables(self):
        for table_name in DB_TABLE_SCHEMAS.keys():
            table = self.get_table(table_name)
            if table:
                table.delete()

    def get_table(self, table_name):
        table = None
        if table_name in self.get_table_names():
            table = self.db_resource.Table(table_name)
        return table

    def get_table_attributes(self, table_name):
        table = self.get_table(table_name)
        return table.attribute_definitions

    def get_table_data(self, table_name):
        table = self.get_table(table_name)
        return table.scan()

    def get_table_names(self):
    #   table_names = self.db_client.list_tables()["TableNames"]
        table_names = [table.name for table in self.db_resource.tables.all()]
        return table_names

# Database tasks functions .................................................. #

    def create_task(self, command):
        fields = {
            "state_": "pending", "command": command, "diagnostic": "",
            "created_at": self.datetime_now_utc_iso(),
            "run_at": ""
        }
        return self.create_unique_item(self.tasks_table, "task", fields)

    def create_timer(self, command, crontab):
        fields = {
            "state_": "timer", "command": command, "diagnostic": "",
            "crontab": crontab,
            "created_at": self.datetime_now_utc_iso(),
            "run_at": self.datetime_epoch()[1]
        }
        return self.create_unique_item(self.tasks_table, "task", fields)

# TODO: FIX: to always find the maximum id, not be confused by id_last["Count"]
#       This is a potential problem when there is a gap in the task ids
#       Avoid deleting tasks until the problem is resolved

    def create_unique_item(self, table, item_type, fields=None):
        id_key = id_value = item_type
        id_new = 1
        saved = False

        id_last = table.query(
            KeyConditionExpression=Key(id_key).eq(id_value),
            ScanIndexForward=False,
            Limit=1
        )
        if id_last["Count"] > 0:
            id_new = int(id_last["Items"][0]["id"]) + 1

        while not saved:  # put new item, but only if the item doesn't exist
            try:
                id = str(id_new)
                item = {id_key: id_value, "id": id}
                if fields:
                    item.update(fields)
                condition_expr = f"attribute_not_exists({id_value})"
                table.put_item(Item=item, ConditionExpression=condition_expr)
                saved = True
        #   except dynamo.meta.table.exceptions.ConditionalCheckFailedException
            except Exception as exception:   # handle race condition, try again
                id_new += 1
        return int(id_new)

# TODO: FIX: create_unique_item() problem with gaps in the task ids

    def delete_task(self, task_id):
        if self.delete_task_warning:
            self.delete_task_warning = False
            print("Warning: Using Database.delete_task() may cause problems")
        self.tasks_table.delete_item(
            Key={"task": "task", "id": str(task_id)})

    def get_task(self, task_id):
        key = {"task": "task", "id": str(task_id)}
        result = self.tasks_table.get_item(Key=key)
        return result.get("Item")

    def get_tasks(self, task_id=None, filter=None, sort_field=None):
        if not task_id:
            key_condition_expr = Key("task").eq("task")
        else:
            key_condition_expr = Key("task").eq("task") & Key("id").eq(task_id)

        if not filter:  # ("key", "value"), e.g ("state_", "pending")
            results = self.tasks_table.query(
                KeyConditionExpression=key_condition_expr)["Items"]
        else:
            filter_expr=Attr(filter[0]).eq(filter[1])
            results = self.tasks_table.query(
                KeyConditionExpression=key_condition_expr,
                FilterExpression=filter_expr)["Items"]

        if sort_field:
            if sort_field in "id":
                get_key_function = lambda d: int(d.get(sort_field, ""))
            else:
                get_key_function = lambda d: d.get(sort_field, "")
            results = sorted(results, key=get_key_function)
        return results

    def print_tasks(self, tasks, field_names=None, prefix="  Task"):
        if field_names:
            if field_names != "all":
                tasks = self.filter_dicts_by_keys(tasks, field_names)
        for task in tasks:
            if not field_names:
                command = task["command"]
                created_at = self.utc_iso_to_local(task["created_at"])
                id = int(task["id"])
                state_ = task["state_"]
                if state_ == "timer":
                    command = f"[{task['crontab']}] {command}"
                print(f"{prefix} {id:06d}: {created_at} {state_:7}: {command}")
            else:
                pprint(task)

    def update_task(self, task_id, fields):
        key = {"task": "task", "id": task_id}
        expression_attr_values = {}
        update_expr = "SET"

        index = 0
        for field_name, field_value in fields.items():
            if index > 0:
                update_expr += ","
            variable_name = f"var{index}"
            update_expr += f" {field_name} = :{variable_name}"
            expression_attr_values[f":{variable_name}"] = field_value
            index += 1

        self.tasks_table.update_item(
            Key=key,
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expression_attr_values
        )

    def valid_task_field_name(self, field_name):
        return field_name in DB_TASK_FIELD_NAMES

# Database miscellaneous functions .......................................... #

    def datetime_epoch(self):
        epoch = "1970-01-01T00:00:00.000000"
        return datetime(1970, 1, 1), epoch

    def datetime_now_utc_iso(self):
        return datetime.utcnow().isoformat()

    def utc_iso_since_epoch(self, datetime_utc_iso):
        datetime_utc = self.utc_iso_to_datetime(datetime_utc_iso)
        return (datetime_utc - self.datetime_epoch()[0]).total_seconds()

    def utc_iso_to_datetime(self, datetime_utc_iso):
    #   datetime_utc = date.fromisoformat(datetime_utc_iso)  # should work :(
        strp_isoformat = "%Y-%m-%dT%H:%M:%S.%f"
        datetime_utc = datetime.strptime(datetime_utc_iso, strp_isoformat)
        return datetime_utc

    def utc_iso_to_local(self, datetime_utc_iso):
        datetime_utc = self.utc_iso_to_datetime(datetime_utc_iso)
        datetime_local = datetime_utc.replace(
            tzinfo=timezone.utc).astimezone(tz=None)
        return datetime_local.isoformat().replace("T", " ")[:19]

    # Filter a list of keys and values from a list of dictionaries
    #     dicts: [{"a": 1, "b:2"}], keys: ["a"] --> [{"a": 1}]

    def filter_dicts_by_keys(self, dicts, keys):
        results = [{key: d[key] for key in keys if key in d} for d in dicts]
        return results

    def team_exists(self, team, submission_hash):  # TODO: Refactor this
        try:
            key = {"team": team, "commit_id": submission_hash}
            results = self.datapoints_table.get_item(Key=key)
            return "Item" in results
        except BotocoreClientError as botocore_client_error:
            diagnostic = f"AWS Boto3 Error: {botocore_client_error}"
            if "UnrecognizedClientException" in str(botocore_client_error):
                diagnostic = f"AWS boto3 Error: Security token is invalid"
            raise SystemExit(diagnostic)
        
# --------------------------------------------------------------------------- #

class TaskManager():
    def __init__(self, database):
        self.database: Database = database

    def process_start(self, task, new_state):
        task_id = task["id"]
        command = task["command"]
        run_previous = task["run_at"]
        task["run_at"] = self.database.datetime_now_utc_iso()
        task["state_"] = new_state
        if new_state != "timer":
            self.database.update_task(task_id, {"run_at": task["run_at"]})
        self.database.update_task(task_id, {"state_": task["state_"]})
        if task["diagnostic"] != "":
            task["diagnostic"] = ""
            self.database.update_task(
                task_id, {"diagnostic": task["diagnostic"]})
        return task_id, command, run_previous

    def process_task(self, task):
        task_id, command, run_previous = self.process_start(task, "running")
        tokens = command.split()
        if tokens[0] == "echo":
            print(f"---- {' '.join(tokens[1:])}")
        elif tokens[0] == "sleep":
            time.sleep(int(tokens[1]))
        else:
            try:
                result = subprocess.run(
                    tokens, check=True, shell=False, timeout=None)
            except (FileNotFoundError, PermissionError) as error:
                task["diagnostic"] = f"Error: {error}"
                task["state_"] = "error"
                print(f"BOOM {task['diagnostic']}")
            except subprocess.CalledProcessError as called_process_error:
                error_code = called_process_error.returncode
                task["diagnostic"] =  \
                    f"Error code {error_code}: {' '.join(command)}"
                task["state_"] = "error"
                print(f"BOOM {task['diagnostic']}")

    # TODO: Replace individual update_task() with table.put_item() ?
    # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/dynamodb.html#creating-a-new-item

        if task["state_"] != "error":
            task["state_"] = "success"
        else:
            self.database.update_task(
                task_id, {"diagnostic": task["diagnostic"]})

        self.database.update_task(task_id, {"state_": task["state_"]})

    def crontab_error(self, task):
        task_id = task["id"]
        diagnostic = f"Error: Invalid crontab field: {task['crontab']}"
        print(f"Timer {int(task_id):06d}: {diagnostic}")
        self.database.update_task(
            task_id, {"diagnostic": task["diagnostic"]})
        task["state_"] = "error"
        self.database.update_task(task_id, {"state_": task["state_"]})

    def process_timer(self, task):
        task_id, command, run_previous = self.process_start(task, "timer")
        crontabs = task["crontab"].split()
        if len(crontabs) != 6:
            self.crontab_error(task)
        else:
            time_scales = [1, 60, 3600, 86400]  # seconds
            for time_index in range(len(time_scales)):
                time_scale = time_scales[time_index]
                crontab = crontabs[time_index]
                if "/" in crontab:
                    try:
                        absolute_time, relative_time = crontab.split("/")
                    except ValueError as value_error:
                        self.crontab_error(task)

                    run_previous = self.database.utc_iso_since_epoch(
                        run_previous)
                    run_previous_delta = time.time() - run_previous
                    if run_previous_delta >= int(relative_time) * time_scale:
                        new_task_id = self.database.create_task(command)
                        task["run_at"] = self.database.datetime_now_utc_iso()
                        self.database.update_task(
                            task_id, {"run_at": task["run_at"]})
                        new_task = self.database.get_task(new_task_id)
                        self.database.print_tasks(
                            [new_task], prefix="---- Create")

    def run(self, run_loop_sleep_time=RUN_LOOP_SLEEP_TIME):
        while True:
            loop_start_time = time.time()

            for task_state in ["timer", "pending"]:
                filter = ("state_", task_state)
                tasks = self.database.get_tasks(filter=filter)
            #   print(f"## Fetched {task_state} Tasks: count={len(tasks)}")

                for task in tasks:
                    if task_state == "timer":
                        self.process_timer(task)
                    if task_state == "pending":
                        task_start_time = time.time()
                        prefix = "vvvv Running Task"
                        self.database.print_tasks([task], prefix=prefix)
                        self.process_task(task)
                        task_process_time = time.time() - task_start_time
                        prefix = "^^^^ Task processing: "
                        print(f"{prefix}{task_process_time:.1f} seconds")

            loop_processing_time = time.time() - loop_start_time
            sleep_time = max(0, run_loop_sleep_time - loop_processing_time)
            print(f"## Tasks processing: {loop_processing_time:.1f} seconds, "
                  f"sleeping: {sleep_time:.1f} seconds")
            time.sleep(run_loop_sleep_time)

# --------------------------------------------------------------------------- #

def check_database(database):
    table_names = database.get_table_names()
    print(f"## DB tables: {table_names}")

    print("\n-------------------------------")
    for table_name in table_names:
        print(f"## DB Table: {table_name}")
    #   database.describe_table(table_name)  # low-level
        table_attributes = database.get_table_attributes(table_name)
        print(f"DB table attributes: {table_attributes}")
        print()

        table_data = database.get_table_data(table_name)
        table_item_count = table_data["Count"]
        table_items = table_data["Items"]
        print(f"DB table item count: {table_item_count}")
        if table_item_count == 1:
            print(f"DB table items: {table_items[0]}")
        if table_item_count > 1:
            print(f"DB table items: {table_items[0].keys()}")
        print("\n-------------------------------")

    print(f"DB Team exists: {database.team_exists('team1', 'hash1')}")

    print("\n-------------------------------")
    task_id = database.create_task("echo 0")  # create: 1
    task_id = database.create_task("echo 2")  # create: 2
    task_id = database.create_task("echo 3")  # create: 3
    database.delete_task(task_id)             # delete: 3, FIX: (task_id - 1)

    print(f"DB Task 1")
    task = database.get_task("1")
    if task:
        database.print_tasks([task])
    print(f"DB Tasks")
    database.print_tasks(database.get_tasks(sort_field="id"))

    print("\n-------------------------------")
    database.update_task("1", {"command": "echo 1"})
    database.print_tasks([database.get_task("1")])

def load_configuration(configuration_file):
    try:
        with open(configuration_file) as file:
            configuration = json.load(file)
            aws_access_key_id = configuration["AWS_ACCESS_KEY_ID"]
            aws_secret_access_key = configuration["AWS_SECRET_ACCESS_KEY"]
    except FileNotFoundError as file_not_found_error:
        raise SystemExit(str(file_not_found_error))
    except KeyError as key_error:
        raise SystemExit(
            f"Configuration: '{configuration_file}' requires {key_error}")
    return aws_access_key_id, aws_secret_access_key

def validate_field_name(database, field_name):
    if not database.valid_task_field_name(field_name):
        diagnostic = f"Error: Invalid field name: {field_name}\n"  \
                     f"Valid field names: {' '.join(DB_TASK_FIELD_NAMES)}"
        raise SystemExit(diagnostic)

@click.group("main")
@click.pass_context
def main(context):
    """Task Manager server"""
    aws_access_key_id, aws_secret_access_key = load_configuration(
        CONFIGURATION_PATHNAME)
    database = Database(aws_access_key_id, aws_secret_access_key)
    context.obj = TaskManager(database)

@main.command(help="Check (test) database")
@click.pass_obj
def check(task_manager):
    check_database(task_manager.database)

@main.command(name="create", help="Create task")
@click.pass_obj
@click.argument("command", nargs=1, required=True, default=None)
def create_task(task_manager, command):
    database = task_manager.database
    task_id = database.create_task(command)
    task = database.get_task(task_id)
    database.print_tasks([task])

@main.command(name="timer")
@click.pass_obj
@click.argument("command", nargs=1, required=True, default=None)
@click.argument("crontab", nargs=1, required=True, default=None)
def create_timer(task_manager, command, crontab):
    """CRONTAB field ... inspired by, but not exactly the same as Unix crontab

    \b
    .------------------------ second       (0 - 59)
    |   .-------------------- minute       (0 - 59)
    |   |   .---------------- hour         (0 - 23)
    |   |   |   .------------ day of month (1 - 31)
    |   |   |   |   .-------- month        (1 - 12)
    |   |   |   |   |   .---- day of week  (1 - 7): Monday = 1
    |   |   |   |   |   |
    *   *   *   *   *   *     "*" is a wildcard, i.e matches any value.

    \b
    0   0   0   *   *   *     "n" matches exact value, e.g just at midnight
    0   *   0/4 *   *   *     "Absolute time/Relative time", e.g every 4 hours
    *   0/1 *   *   *   *     "Absolute time/Relative time", e.g every minute
    """
    database = task_manager.database
    timer_id = database.create_timer(command, crontab)
    timer = database.get_task(timer_id)
    database.print_tasks([timer])

@main.command(name="delete", help="Delete task")
@click.pass_obj
@click.argument("task_id", nargs=1, required=True, default=None)
def delete_task(task_manager, task_id):
    task_manager.database.delete_task(task_id)

@main.command(help="Destroy database tables")
@click.pass_obj
def destroy(task_manager):
    confirm = "YES"
    if not DB_URL:  # using AWS DynamoDB production database ?
        confirm = input('To destroy the production database, type "YES": ')
    if confirm == "YES":
        task_manager.database.destroy_tables()
        print("Database table(s) deleted")

@main.command(name="list",
    help="List tasks optionally searching by field, e.g command, id, state")
@click.pass_obj
@click.option("--all", "-a", is_flag=True, help="Show all Task fields")
@click.option("--field", "-f", nargs=2, help="List Tasks with this field value")
def list_tasks(task_manager, all, field):
    database = task_manager.database
    filter = None
    tasks = None
    if field:
        field_name, field_value = field
        if field_name == "id":
            task = database.get_task(field_value)
            if not task:
                raise SystemExit(f"Error: Task id {field_value} not found")
            tasks = [task]
        else:
            if field_name == "state":
                field_name = "state_"
            validate_field_name(database, field_name)
            filter = (field_name, field_value)
    if not tasks:
        tasks = database.get_tasks(filter=filter, sort_field="id")
    database.print_tasks(tasks, "all" if all else None)

@main.command(help="Run task_manager server")
@click.pass_obj
@click.option("--sleep", "-s", nargs=1, default=RUN_LOOP_SLEEP_TIME,
    help="Run loop sleep time")
def run(task_manager, sleep):
    task_manager.run(run_loop_sleep_time=sleep)

@main.command(name="update", help="Update task field, e.g command, state")
@click.pass_obj
@click.argument("task_id", nargs=1, required=True, default=None)
@click.argument("field_name", nargs=1, required=True, default=None)
@click.argument("field_value", nargs=1, required=True, default=None)
def update_task(task_manager, task_id, field_name, field_value):
    database = task_manager.database
    if field_name == "state":
        field_name = "state_"
    validate_field_name(database, field_name)
    database.update_task(task_id, {field_name: field_value})
    task = database.get_task(task_id)
    database.print_tasks([task])

if __name__ == "__main__":
    main()

# --------------------------------------------------------------------------- #
