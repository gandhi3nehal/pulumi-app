import json
import pulumi
import pulumi_aws as aws
from pulumi_aws import s3, dynamodb
from pulumi import ComponentResource, Output, ResourceOptions

# Define our ComponentResource subclasses.
class MyResources(ComponentResource):
    bucket_arn: Output[str]
    bucket_url: Output[str]
    bucket_id: Output[str]
    table_name: Output[str]
    

    def __init__(self, name: str, opts: pulumi.ResourceOptions = None):
        super().__init__("my:modules:MyResources", name, {}, opts)


    def createDynamoTable(self):
        dynamodb_table = dynamodb.Table('mytable',
            attributes=[
                {
                    'name': 'key',
                    'type': 'S',
                },
                {
                    'name': 'TS',
                    'type': 'S'
                }
            ],
        hash_key="key",
        range_key="TS",
        read_capacity=1,
        write_capacity=1,)
        self.table_name = dynamodb_table.name


    def createBucket(self):
        bucket = s3.Bucket("gnehal-mybucket", opts=ResourceOptions(parent=self))
        # Register output properties for this component
        self.bucket_arn = bucket.arn
        self.bucket_url = bucket.website_endpoint
        self.bucket_id = bucket.id

    def regout(self):
        # To finish creating this component, we must call `register_outputs`
        # to signify that we are done creating this `ComponentResource`.
        self.register_outputs({
            "bucketArn": self.bucket_arn,
            "bucketUrl": self.bucket_url,
            "bucketId": self.bucket_id,
            "name": self.table_name,
        })

# Usage
my_resource = MyResources("myresources")

my_resource.createBucket()
my_resource.createDynamoTable()

my_resource.regout()

# Exports
pulumi.export('bucket_arn', my_resource.bucket_arn)
pulumi.export('bucket_url', my_resource.bucket_url)

# Export the name of the DynamoDB table
pulumi.export('TableName', my_resource.table_name)


# Create IAM Policy for DynamoDB
dynamo_db_policy = aws.iam.Policy("dynamoDbPolicy",
    policy=pulumi.Output.all().apply(lambda _: {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:Scan",
                "dynamodb:Query",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem"
            ],
            "Resource": "*"
        }]
    })
)

# An execution role to use for the Lambda function
role = aws.iam.Role("role", 
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com",
            },
        }],
    }),
    managed_policy_arns=[aws.iam.ManagedPolicy.AWS_LAMBDA_BASIC_EXECUTION_ROLE])

role_policy_attachment = aws.iam.RolePolicyAttachment("lambdaDynamoDbAttachment",
    role=role.name,
    policy_arn=dynamo_db_policy.arn
)

# A Lambda function to invoke
fn = aws.lambda_.Function("fn",
    runtime="python3.9",
    handler="handler.handler",
    role=role.arn,
    environment=aws.lambda_.FunctionEnvironmentArgs(
                variables={"TABLE_NAME": my_resource.table_name},
    ),
    code=pulumi.FileArchive("./function"))

allow_bucket = aws.lambda_.Permission("allowBucket",
    action="lambda:InvokeFunction",
    function=fn.arn,
    principal="s3.amazonaws.com",
    source_arn=my_resource.bucket_arn)

# Create an S3 bucket notification configuration
notification_configuration = aws.s3.BucketNotification("bucketNotification",
    bucket=my_resource.bucket_id,
    lambda_functions=[
        aws.s3.BucketNotificationLambdaFunctionArgs(
            lambda_function_arn=fn.arn,
            events=["s3:ObjectCreated:*"],
        ),
    ],
)



