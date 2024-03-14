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