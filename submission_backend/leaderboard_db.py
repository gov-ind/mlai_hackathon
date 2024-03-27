from decimal import Decimal
import time
import boto3
from boto3.dynamodb.conditions import Key
import json

LOG_FILE = "database/evaluated_repos.json"
LEADERBOARD_DB_URL = "http://localhost:8000"

def convert_floats_to_decimal(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_floats_to_decimal(value) for key, value in obj.items()}
    else:
        return obj
    
def convert_decimals_to_floats(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, list):
        return [convert_decimals_to_floats(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals_to_floats(value) for key, value in obj.items()}
    else:
        return obj

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)  # Convert Decimals to floats
    raise TypeError ("Type not serializable")

class LeaderboardDBClient():
    def __init__(self, aws_access_key_id, AWS_SECRET_ACCESS_KEY) -> None:
        self.session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name='us-east-1'
        )

        self.table_name = 'leaderboard'
        db_args = {"service_name": "dynamodb"}
        if LEADERBOARD_DB_URL:
            db_args["endpoint_url"] = LEADERBOARD_DB_URL

        self.dynamodb = self.session.resource(**db_args)
    
        # create table if it does not exist already
        if self.table_name not in [table.name for table in self.dynamodb.tables.all()]:
            table = self.dynamodb.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {
                        'AttributeName': 'team_id',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'git_commit_hash',
                        'KeyType': 'RANGE'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'team_id',
                        'AttributeType': 'N'
                    },
                    {
                        'AttributeName': 'git_commit_hash',
                        'AttributeType': 'S'
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            )
            table.meta.client.get_waiter('table_exists').wait(TableName=self.table_name)

        self.table = self.dynamodb.Table(self.table_name)
        
    def is_already_submitted(self, team_id, submission_hash):
        response = self.table.get_item(
            Key={
                'team_id': team_id,
                'git_commit_hash': submission_hash
            }
        )
        return 'Item' in response

    def submit(self, submission):
        assert 'team_id' in submission, f'team_id (primary key) not found in {submission}'
        assert 'git_commit_hash' in submission, f'git_commit_hash (secondary key) not found in {submission}'
        
        cloned_submission = convert_floats_to_decimal(submission.copy())
        cloned_submission['submitted_at'] = int(round(time.time() * 1000))

        response = self.table.put_item(Item=cloned_submission)

        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise ValueError(f"Failed to submit {submission}, response was {response}")
        
    def upsert_submission(self, submission):
        assert 'team_id' in submission, f'team_id (primary key) not found in {submission}'
        assert 'git_commit_hash' in submission, f'git_commit_hash (secondary key) not found in {submission}'

        team_id = submission['team_id']
        submission_hash = submission['git_commit_hash']

        existing_submission = self.table.get_item(
            Key={
                'team_id': team_id,
                'git_commit_hash': submission_hash
            }
        )

        if 'Item' not in existing_submission:
            self.submit(submission)
        else:
            self.update_submission(submission)

    def update_submission(self, new_data):
        assert 'team_id' in new_data, f'team (primary key) not found in {new_data}'
        assert 'git_commit_hash' in new_data, f'git_commit_hash (secondary key) not found in {new_data}'

        team_id = new_data['team_id']
        submission_hash = new_data['git_commit_hash']

        existing_submission = self.table.get_item(
            Key={
                'team_id': team_id,
                'git_commit_hash': submission_hash
            }
        )

        if 'Item' not in existing_submission:
            raise ValueError(f"Submission {team_id}/{submission_hash} not found")
        
        existing_submission = existing_submission['Item']
        
        trial_data = new_data['main_trial']
        existing_trial_data = existing_submission['main_trial']

        for timestamp in existing_trial_data['timestamps']:
            if timestamp in trial_data['timestamps']:
                raise ValueError(f"Timestamp {timestamp} shared between both trials, {trial_data}, {existing_trial_data}")
        
        if existing_trial_data['timestamps'][-1] + 300 != trial_data['timestamps'][0]:
            raise ValueError(f"Timestamps not continuous between trials, {trial_data}, {existing_trial_data}")


        combined_trial = {}
        for k, v in trial_data.items():
            combined_trial[k] = existing_trial_data[k] + v

        existing_submission['main_trial'] = combined_trial
        existing_submission['score'] = combined_trial['profits'][-1]

        existing_submission = convert_floats_to_decimal(existing_submission.copy())
        existing_submission['submitted_at'] = int(round(time.time() * 1000))

        response = self.table.put_item(Item=existing_submission)

        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise ValueError(f"Failed to update {new_data}, response was {response}")

    def delete_submission(self, team_id, submission_hash):
        response = self.table.delete_item(
            Key={
                'team_id': team_id,
                'git_commit_hash': submission_hash
            }
        )

        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise ValueError(f"Failed to delete {team_id}/{submission_hash}, response was {response}")

    def save_whole_database_to_json(self, outfile):
        response = self.table.scan()
        with open(outfile, 'w') as f:
            # Use the custom default function for JSON serialization
            json.dump(response, f, default=decimal_default, indent=4)

    def load_all_submissions(self, team_id):
        response = self.table.query(
            KeyConditionExpression=Key('team_id').eq(team_id)
        )
        items = response['Items']

        items = [convert_decimals_to_floats(item) for item in items]
        return items
    
    def load_latest_submission(self, team_id, commit_hash):
        response = self.table.query(
            KeyConditionExpression=Key('team_id').eq(team_id) & Key('git_commit_hash').eq(commit_hash)
        )

        if 'Items' not in response:
            return None

        items = response['Items']

        if len(items) > 1:
            raise ValueError(f"Multiple submissions found for {team_id}/{commit_hash}, {items}")
        
        if len(items) == 0:
            return None
        
        item = convert_decimals_to_floats(items[0])
        return item
    
    def destroy_table(self):
        tables = list(self.dynamodb.tables.all())
        for table in tables:
            # delete table if it is called leaderboard
            if table.name == self.table_name:
                table.delete()