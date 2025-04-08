import io
import json
import os
import csv

import boto3

CACHE_BUCKET = os.getenv('CACHE_BUCKET')
FLOW_IDENTIFIER = os.getenv('FLOW_IDENTIFIER')
FLOW_ALIAS = os.getenv('FLOW_ALIAS')

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
        params = event['queryStringParameters']
        if not params:
            return {
                'statusCode': 400,
                'body': json.dumps('Missing query parameters')
            }
        invocation = params.get('invocation')
        if not invocation:
            return {
                'statusCode': 400,
                'body': json.dumps('Missing invocation parameter')
            }
        if invocation not in ['summarize', 'recommend']:
            print(f'Invalid invocation parameter: {invocation}')
            return {
                'statusCode': 400,
                'body': json.dumps('Invalid invocation parameter')
            }
        state_abbr = params.get('state')
        if not state_abbr:
            return {
                'statusCode': 400,
                'body': json.dumps('Missing state parameter')
            }
        state_abbr = state_abbr.upper()
        if  state_abbr not in state_abbrev_to_full:
            print(f'Invalid state parameter: {state_abbr}')
            return {
                'statusCode': 400,
                'body': json.dumps('Invalid state parameter')
            }
        state_full = state_abbrev_to_full[state_abbr]
        print(f'Input: invocation={invocation} state={state_abbr},{state_full}')

        s3 = boto3.client('s3', region_name='us-east-1')
        if not state_is_cached(s3, state_abbr, invocation):
            print(f'State {state_full} is not cached, getting new response for {invocation}')
            data = get_data_from_s3(s3, state_abbr)
            print(f'Data to provide the models: {data}')
            response = get_new_response(state_full, invocation, data)
            if not response:
                return {
                    'statusCode': 500,
                    'body': json.dumps('Error receiving response from model')
                }
            cache_response(s3, state_abbr, response, invocation)
        else:
            print(f'State {state_full} is cached, getting cached response for {invocation}')
            response = get_cached_response(s3, state_abbr, invocation)
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,GET'
            },
            'body': json.dumps({
                'info': response
            }),
        }
    except Exception as e:
        print(f'Error: {e}')
        return {
            'statusCode': 500,
            'body': 'Internal error'
        }

def state_is_cached(s3, state, path) -> bool:
    key = f'{path}/{state}.txt'
    try:
        print(f'Checking if {key} exists in {CACHE_BUCKET}')
        s3.head_object(Bucket=CACHE_BUCKET, Key=key)
        return True
    except Exception:
        return False

def get_cached_response(s3, state, path) -> str:
    key = f'{path}/{state}.txt'
    try:
        print(f'Getting cached response for {key} in {CACHE_BUCKET}')
        response = s3.get_object(Bucket=CACHE_BUCKET, Key=key)
        data = response['Body'].read().decode('utf-8')
        print(f'Cached response: {data}')
        return data
    except Exception as e:
        print(f'Error decoding s3 object: {e}')
        return 'Error'

def cache_response(s3, state, data, path) -> None:
    key = f'{path}/{state}.txt'
    print(f'Caching response for {key} in {CACHE_BUCKET}')
    s3.upload_fileobj(io.BytesIO(data.encode('utf-8')), CACHE_BUCKET, key)

def csv_to_dict(file_input):
    result_dict = {}
    csv_reader = csv.DictReader(file_input)
    first_column = csv_reader.fieldnames[0]
    for row in csv_reader:
        key = row[first_column]
        result_dict[key] = row

    return result_dict

def get_data_from_s3(s3, state_abbr) -> dict:
    key = 'energy-by-state-and-type.csv'
    print(f'Getting data from {key} in {CACHE_BUCKET}')
    response = s3.get_object(Bucket=CACHE_BUCKET, Key=key)
    csv_string = response['Body'].read().decode('utf-8')
    data = csv_to_dict(io.StringIO(csv_string))
    return data[state_abbr]

def get_new_response(state_full, invocation, data):
    bedrock = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
    print(f'Invoking flow for {invocation} of {state_full}, flow_id={FLOW_IDENTIFIER}, flow_alias={FLOW_ALIAS}')
    prompt = f"""
        Invocation: {invocation}
        State: {state_full}
        Data: {data}
    """
    print(f'Prompt: {prompt}')
    response = bedrock.invoke_flow(
        enableTrace=True,
        flowIdentifier=FLOW_IDENTIFIER,
        flowAliasIdentifier=FLOW_ALIAS,
        inputs=[
            {
                'content': {
                    'document': prompt
                },
                'nodeName': 'FlowInputNode',
                'nodeOutputName': 'document'
            },
        ],
    )
    # Wait for response through Boto3 EventStream https://botocore.amazonaws.com/v1/documentation/api/latest/reference/eventstream.html
    for event in response['responseStream']:
        if event:
            print(f'Received event: {event}')
            if 'flowOutputEvent' in event:
                print('Received a flowOutputEvent')
                output_event = event['flowOutputEvent']['content']
                document = output_event['document']
                print(f'Received document: {document}')
                return document

    return None
