import random
import json
from submission_backend.leaderboard_db import LeaderboardDBClient
from poll import submit_output, get_docker_client
import uuid


with open('.credentials.json') as f:
    credentials = json.load(f)

db_client = LeaderboardDBClient(credentials['AWS_ACCESS_KEY_ID'], credentials['AWS_SECRET_ACCESS_KEY'])
docker_client = get_docker_client()


teams = ['steam-team', 'dream-team', 'cream-team', 'scream-team', 'team-team']
s = 0

for team in teams:
    for i in range(random.randint(1, 7)):
        s +=1   
        if random.random() > 0.7:
            repo_name = 'THIS_DIRECTORY_DOES_NOT_EXIST' 
        else:
            repo_name = './'
        submit_output(docker_client, db_client, repo_name=team, tag_name=f'submission-{s}', commit_sha=str(uuid.uuid4()), repo_dir=repo_name, clone=False)      
        print('submitted', team, i)
