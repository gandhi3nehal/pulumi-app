import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";


// Define our custom component resource class by extending pulumi.ComponentResource
class MyAwsBucket extends pulumi.ComponentResource {
    public readonly bucket: aws.s3.Bucket;
    
    constructor(name: string, args: pulumi.ComponentResourceOptions = {}) {
        super("my:component:MyAwsBucket", name, {}, args);

        // Create an S3 Bucket
        this.bucket = new aws.s3.Bucket(`${name}-bucket`, {}, { parent: this });

        // Ensure that we pass along our options to the parent class.
        this.registerOutputs({
            bucket: this.bucket,
        });
    }
}

// Define our custom component resource class by extending pulumi.ComponentResource
class MyAwsLambda extends pulumi.ComponentResource {
    public readonly lambdaFunc: aws.lambda.Function;
    

    constructor(name: string, args: pulumi.ComponentResourceOptions = {}) {
        super("my:component:MyAwsLambda", name, {}, args);

        // Create a Lambda Function
        const lambdaRole = new aws.iam.Role(`${name}-lambdaRole`, {
            assumeRolePolicy: aws.iam.assumeRolePolicyForPrincipal({ Service: "lambda.amazonaws.com" }),
        }, { parent: this });

        new aws.iam.RolePolicyAttachment(`${name}-lambdaRolePolicy`, {
            role: lambdaRole.name,
            policyArn: aws.iam.ManagedPolicies.AWSLambdaBasicExecutionRole,
        }, { parent: this });

        new aws.iam.RolePolicyAttachment(`${name}-lambdaRoleDynamoPolicy`, {
            role: lambdaRole.name,
            policyArn: aws.iam.ManagedPolicies.AmazonDynamoDBFullAccess,
        }, { parent: lambdaRole });

        this.lambdaFunc = new aws.lambda.Function(`${name}-lambda`, {
            code: new pulumi.asset.AssetArchive({ // Place your zipped Lambda code here
                ".": new pulumi.asset.FileArchive("./function"),
            }),
            role: lambdaRole.arn,
            handler: "handler.handler",
            runtime: aws.lambda.Python3d8Runtime,
            environment: {
                variables: {
                    TABLE_NAME: myDynamotable.dynamodbTable.name,
                },
            },
        }, { parent: this });

        new aws.lambda.Permission(`${name}-lambdaPerm`, {
            action: "lambda:InvokeFunction",
            function: this.lambdaFunc,
            principal: "s3.amazonaws.com",
            sourceArn: myBucket.bucket.arn,
        }, { parent: this.lambdaFunc });

        new aws.s3.BucketNotification(`${name}-bucketNotification`, {
            bucket: myBucket.bucket.id,
            lambdaFunctions: [{
                lambdaFunctionArn: this.lambdaFunc.arn,
                events: ["s3:ObjectCreated:*"],
            }],
        }, { parent: myBucket.bucket, dependsOn: [this.lambdaFunc] });

        // Ensure that we pass along our options to the parent class.
        this.registerOutputs({
            lambdaFunc: this.lambdaFunc,
        });
    }
}

// Define our custom component resource class by extending pulumi.ComponentResource
class MyAwsDynamotable extends pulumi.ComponentResource {
    public readonly dynamodbTable: aws.dynamodb.Table;
    

    constructor(name: string, args: pulumi.ComponentResourceOptions = {}) {
        super("my:component:MyAwsDynamotable", name, {}, args);

        // Create a DynamoDB Table
        this.dynamodbTable = new aws.dynamodb.Table(`${name}-table`, {
            attributes: [
                {
                    name: "key",
                    type: "S"
                },
                {
                    name: "TS",
                    type: "S"
                }
            ],
            hashKey: "key",
            rangeKey: "TS",
            readCapacity: 1,
            writeCapacity: 1,    
            }, { parent: this });

        // Ensure that we pass along our options to the parent class.
        this.registerOutputs({
            dynamodbTable: this.dynamodbTable,
        });
    }
}



const myBucket = new MyAwsBucket("mybucket");
const myDynamotable = new MyAwsDynamotable("myDynamotable");
const myLambda = new MyAwsLambda("myLambda");


// Export the names of the resources
export const bucketName = myBucket.bucket.id;
export const lambdaFunctionName = myLambda.lambdaFunc.name;
export const dynamoTableName = myDynamotable.dynamodbTable.name;
