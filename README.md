# CNF Remediation Assistant

# Troubleshooting Cloudformation Failures with Generative AI


## Create an SNS Topic to send an email

In this section we will create an SNS Topic in us-west-2 that will be used by the lambda function to send an email of the CFN root cause analysis. 

[notes](https://docs.aws.amazon.com/sns/latest/dg/sns-email-notifications.html)

1. Create a standard SNS topic
2. Create a subscription to that topic with email as the protocol
3. Enter your email address duanlig@amazon.com
4. Clear create subscription
5. Copy the ARN

>NOTE: You will receive an email to confirm the subscription

## Lambda Function

In this section we create the lambda that will process the cloudformation event and send to bedrock to determine the root cause analysis. ENV - Topic ARN, REGION

1. Ensure that bedrock Claude 3 Sonnet model access is enabled in your region `us-west-2`

2. Create a lambda role that has access to bedrock and SNS

```python
arn:aws:iam::043174637992:role/service-role/chat-role-z2r9kh6o
```

3. Create a boto3 lambda layer to be used to invoke bedrock:

```bash
s3://lambda-layers-us-west-2-54564546/boto3-bedrock-1-28-57.zip

arn:aws:lambda:us-west-2:043174637992:layer:boto3-layer:1
```

4. Create a lambda function `stackFailureAssistant` in us-west-2. ==NOTE: Update the Lambda Timeout to 3 minutes and memory to 1024==

```python
import os
import boto3
import json


TOPIC_ARN = os.environ["TOPIC_ARN"]
REGION = os.environ["REGION"]


# Define bedrock
bedrock = boto3.client(
    service_name="bedrock-runtime",
    region_name=REGION
)

sns = boto3.client(
        service_name="sns",
        region_name=REGION
    )


def create_prompt(reason: str) -> str:
    prompt = f"""Dear customer,

    I have analyzed the CloudFormation failure reason provided: {reason}. The root cause appears to be <root_cause>. <explain analysis and reasoning>.
    
    To resolve this issue, I would suggest the following next steps:
    
        <step 1>
        <step 2>
        <step 3>
    
    Please let me know if any of those steps need further clarification or if you have additional questions. I'm happy to provide more details if needed.
    
    Thank you, 
    
    Claude
    """
    return prompt


def send_prompt(prompt: str): 
    prompt_config = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                    "type": "text",
                    "text": prompt
                    }
                ]
            }
        ]
    }

    body = json.dumps(prompt_config)

    modelId = "anthropic.claude-3-sonnet-20240229-v1:0"
    contentType = "application/json"
    accept = "application/json"
    response = bedrock.invoke_model(
        body=body, modelId=modelId, accept=accept, contentType=contentType
    )
    response_body = json.loads(response.get("body").read())

    result = response_body.get("content")[0]["text"]
    return result

# Create a function that send text to trigger sns
def send_text(message: str):
    sns.publish(
        TopicArn=TOPIC_ARN,
        Message=message
    )
    return "SNS Successfully SENT"


# Lambda handler
def lambda_handler(event, context):
    reason = event["detail"]["status-details"]["status-reason"]
    prompt = create_prompt(reason)
    response = send_prompt(prompt)
    sns_response = send_text(response)
    return sns_response
```

5. Create a Lambda function test for the CloudFormation example. :

```json
{
  "version": "0",
  "source": "aws.cloudformation",
  "account": "123456789012",
  "id": "12345678-1234-1234-1234-111122223333",
  "region": "us-east-1",
  "detail-type": "CloudFormation Resource Status Change",
  "time": "2022-04-31T17:00:00Z",
  "resources": ["arn:aws:cloudformation:us-east-1:123456789012:stack/teststack"],
  "detail": {
    "stack-id": "arn:aws:cloudformation:us-west-1:123456789012:stack/teststack",
    "logical-resource-id": "my-s3-bucket",
    "physical-resource-id": "arn:aws:s3:us-east-1:123456789012:bucket:my-s3-bucket",
    "status-details": {
      "status": "CREATE_FAILED",
      "status-reason": "Resource handler returned message: "Layers are not in the same region as the function. Layers are expected to be in region us-west-2. (Service: Lambda, Status Code: 400, Request ID: f0e58f60-48d7-4c0b-86db-31ab6a63b8c5)" (RequestToken: b275a4a1-8336-e52e-c73b-2c6e90ced18a, HandlerErrorCode: InvalidRequest)"
    },
    "resource-type": "AWS::S3::Bucket"
  }
}
```


## EventBridge Rule

1. Create a EventBridge rule `cfn-failure-rule` in US-West-2 triggers the lambda.

Description: `This rule triggers a lambda to analyzer cloudformation template failures `

2. Use the following pattern
```json
{
  "source": ["aws.cloudformation"],
  "detail-type": ["CloudFormation Resource Status Change"],
  "region": ["us-west-2"],
  "detail": {
  "status-details": {
      "status": ["CREATE_FAILED"]
		}
	}
}
```

Test rule:

```json
{
  "version": "0",
  "source": "aws.cloudformation",
  "account": "123456789012",
  "id": "12345678-1234-1234-1234-111122223333",
  "region": "us-east-1",
  "detail-type": "CloudFormation Resource Status Change",
  "time": "2022-04-31T17:00:00Z",
  "resources": ["arn:aws:cloudformation:us-east-1:123456789012:stack/teststack"],
  "detail": {
    "stack-id": "arn:aws:cloudformation:us-west-1:123456789012:stack/teststack",
    "logical-resource-id": "my-s3-bucket",
    "physical-resource-id": "arn:aws:s3:us-east-1:123456789012:bucket:my-s3-bucket",
    "status-details": {
      "status": "CREATE_COMPLETE",
      "status-reason": ""
    },
    "resource-type": "AWS::S3::Bucket"
  }
}
```

3. Select the `stackFailureAssistant` target:

## Test

Upload a broken CFN to test. 