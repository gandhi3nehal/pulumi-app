import json
import urllib.parse
import boto3
import os
from datetime import datetime

print('Loading function')

s3 = boto3.client('s3')
dynamodb = boto3.client('dynamodb')



def handler(event, context):
    #print("Received event: " + json.dumps(event, indent=2))

    # Get the object from the event and show its content type
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    print("key: " + key + "bucket: " + bucket)
    now = datetime.now() # current date and time
    date_time = now.strftime("%m/%d/%Y, %H:%M:%S")
    tableName = os.environ['TABLE_NAME'];
    dynamodb.put_item(TableName=tableName, Item={  "key": {
    "S": key
  },
  "TS": {
    "S": date_time
  }
})
