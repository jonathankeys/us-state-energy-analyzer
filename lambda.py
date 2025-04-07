import os
import uuid
import json

import boto3
import io

CACHE_BUCKET = os.getenv('CACHE_BUCKET')

state_abbrev_to_full = {
    'AL': 'Alabama',
    'AK': 'Alaska',
    'AZ': 'Arizona',
    'AR': 'Arkansas',
    'CA': 'California',
    'CO': 'Colorado',
    'CT': 'Connecticut',
    'DE': 'Delaware',
    'FL': 'Florida',
    'GA': 'Georgia',
    'HI': 'Hawaii',
    'ID': 'Idaho',
    'IL': 'Illinois',
    'IN': 'Indiana',
    'IA': 'Iowa',
    'KS': 'Kansas',
    'KY': 'Kentucky',
    'LA': 'Louisiana',
    'ME': 'Maine',
    'MD': 'Maryland',
    'MA': 'Massachusetts',
    'MI': 'Michigan',
    'MN': 'Minnesota',
    'MS': 'Mississippi',
    'MO': 'Missouri',
    'MT': 'Montana',
    'NE': 'Nebraska',
    'NV': 'Nevada',
    'NH': 'New Hampshire',
    'NJ': 'New Jersey',
    'NM': 'New Mexico',
    'NY': 'New York',
    'NC': 'North Carolina',
    'ND': 'North Dakota',
    'OH': 'Ohio',
    'OK': 'Oklahoma',
    'OR': 'Oregon',
    'PA': 'Pennsylvania',
    'RI': 'Rhode Island',
    'SC': 'South Carolina',
    'SD': 'South Dakota',
    'TN': 'Tennessee',
    'TX': 'Texas',
    'UT': 'Utah',
    'US': 'United States',
    'VT': 'Vermont',
    'VA': 'Virginia',
    'WA': 'Washington',
    'WV': 'West Virginia',
    'WI': 'Wisconsin',
    'WY': 'Wyoming'
}

def lambda_handler(event, context):
    try:
        if 'state' not in event:
            return {
                'statusCode': 400,
                'body': 'state is required'
            }
        if 'data' not in event:
            return {
                'statusCode': 400,
                'body': 'data is required'
            }
        if 'id' not in event:
            return {
                'statusCode': 400,
                'body': 'id is required'
            }
        elif event['id'] not in ['summary', 'recommendation']:
            return {
                'statusCode': 400,
                'body': 'id is not valid'
            }
        model_request_type  = event['id']
        data = event['data']
        state_abbr = event['state'].upper()
        state_full = state_abbrev_to_full[state_abbr]

        s3 = boto3.client('s3', region_name='us-east-1')
        if not state_is_cached(s3, state_abbr, model_request_type):
            print(f'State {state_full} is not cached, getting new response for {model_request_type}')
            info = get_new_response(state_full, data, model_request_type)
            cache_response(s3, state_abbr, info, model_request_type)
        else:
            print(f'State {state_full} is cached, getting cached response for {model_request_type}')
            info = get_cached_response(s3, state_abbr, model_request_type)
        return {
            'statusCode': 200,
            'info': info,
        }
    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'body': 'Internal error'
        }

def state_is_cached(s3, state, path):
    key = f'{path}/{state}.txt'
    try:
        s3.head_object(Bucket=CACHE_BUCKET, Key=key)
        return True
    except Exception:
        return False

def get_cached_response(s3, state, path):
    key = f'{path}/{state}.txt'
    response = s3.get_object(Bucket=CACHE_BUCKET, Key=key)
    return response['Body'].read().decode('utf-8')

def cache_response(s3, state, data, path):
    key = f'{path}/{state}.txt'
    bytes = io.BytesIO(data.encode('utf-8'))
    s3.upload_fileobj(bytes, CACHE_BUCKET, key)


def get_agent_info(model_request_type):
    return os.getenv(f'{model_request_type.upper()}_AGENT'), os.getenv(f'{model_request_type.upper()}_ALIAS')


def get_new_response(state_full, data, model_request_type):
    bedrock = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
    agent_id, alias_id = get_agent_info(model_request_type)
    print(f'Invoking model for {model_request_type} for {state_full} with agent ({agent_id}) and alias ({alias_id})')
    if model_request_type == 'summary':
        prompt = (f'Write a 5-10 sentence summary for {state_full}. Reference information about the states profile. Only '
                  f'reference the numbers in {json.dumps(data)}')
    else:
        prompt = (f'Write a 5-10 sentence summary for {state_full} and recommendations of how the state can move towards '
                  f'renewable resources for energy production and consumption. Reference the states profile to better'
                  f'understand the current geography, climate, and resources. Reference the information in '
                  f'{json.dumps(data)} as well when talking about specific numbers of current production and '
                  f'consumption')
    response = bedrock.invoke_agent(
        agentId=agent_id,
        agentAliasId=alias_id,
        sessionId=f'{str(uuid.uuid4())[0:8]}',
        inputText=prompt
    )

    # Wait for response through Boto3 EventStream https://botocore.amazonaws.com/v1/documentation/api/latest/reference/eventstream.html
    for event in response['completion']:
        print(event)
        if event:
            return event['chunk']['bytes'].decode('utf-8')
    return None
