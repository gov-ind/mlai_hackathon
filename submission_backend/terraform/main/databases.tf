resource "aws_dynamodb_table" "teams" {
  name         = "teams"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "info_type"
  range_key    = "team_id"

  attribute {
    name = "info_type" # all items will have the exact same value, something like "team". Max 50 items.
    type = "S"
  }

  attribute {
    name = "team_id"
    type = "N"
  }

  tags = {
    Name = "gbh"
  }
}


resource "aws_dynamodb_table" "leaderboard" {
  name         = "leaderboard"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "team"
  range_key    = "commit_hash"

  attribute {
    name = "team"
    type = "S"
  }

  attribute {
    name = "commit_hash"
    type = "S"
  }

  tags = {
    Name = "gbh"
  }
}

resource "aws_dynamodb_table" "tasks" {
name         = "tasks"
billing_mode = "PAY_PER_REQUEST"
hash_key     = "task"
range_key    = "id"

attribute {
name = "task"
type = "S"
}

attribute {
name = "id"
type = "S"
}

attribute {
name = "team_id"
type = "S"
}

global_secondary_index {
name            = "team_id_index"
hash_key        = "team_id"
projection_type = "ALL"
}

tags = {
Name = "gbh"
}
}