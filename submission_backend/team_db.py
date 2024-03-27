import boto3

LEADERBOARD_DB_URL = "http://localhost:8000"

class TeamDB():
    def __init__(self, aws_access_key_id, AWS_SECRET_ACCESS_KEY) -> None:
        self.session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name='us-east-1'
        )

        db_args = {"service_name": "dynamodb"}
        if LEADERBOARD_DB_URL:
            db_args["endpoint_url"] = LEADERBOARD_DB_URL

        self.dynamodb = self.session.resource(**db_args)
    
        self.table_name = 'teams'
        # create table if it does not exist already
        if self.table_name not in [table.name for table in self.dynamodb.tables.all()]:
            table = self.dynamodb.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {
                        'AttributeName': 'info_type',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'team_id',
                        'KeyType': 'RANGE'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'team_id',
                        'AttributeType': 'N'
                    },
                    {
                        'AttributeName': 'info_type',
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
        

    def upsert_team(self, team):
        self.table.put_item(Item=team)

    def get_team(self, team_id):
        response = self.table.get_item(Key={'info_type': 'team', 'team_id': team_id})
        return response.get('Item', None)

    def delete_team(self, team_id):
        self.table.delete_item(Key={'info_type': 'team', 'team_id': team_id})

    def destroy_table(self):
        for table in self.dynamodb.tables.all():
            if table.name in ['teams']:
                table.delete()