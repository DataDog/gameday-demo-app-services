import boto3
import json
import os

dynamodb = boto3.resource('dynamodb')
reservation_table = dynamodb.Table(os.environ.get('PENPAL_RESERVATION_TABLE'))

def lambda_handler(event, context):
    # Extract the penpal reservation data from the event
    if 'detail' in event:
        # Event is coming from our brick and mortar retail stores
        detail_data = event['detail']
    elif 'body' in event:
        # Event is a direct API POST request from our website
        detail_data = json.loads(event['body'])
    else:
        # The event source is not recognized
        print("Error: Event source not recognized.")
        return {
            'statusCode': 400,
            'body': json.dumps('Event source not recognized.')
        }

    #TODO: Logging event data to test something
    #   Don't forget to remove before prod - wouldn't want any leaky logging!
    print(f"received reservation data: {detail_data}")

    #prepare data for dynamodb
    item={
        'customer_id': detail_data['customer_id'],
        'penpal_email': detail_data['penpal_email'],
        'penpal_type': detail_data['penpal_type'],
    }

    # Add conditional attributes based on penpal type
    if detail_data['penpal_type'] == 'Unicorn':
        item['unicorn_type'] = detail_data['unicorn_type']
        item['unicorn_secret_id'] = detail_data['unicorn_secret_id']
    elif detail_data['penpal_type'] == 'Puppy':
        item['puppy_type'] = detail_data['puppy_type']
        item['puppy_secret_id'] = detail_data['puppy_secret_id']

    # Store the penpal reservation data in dynamodb
    try:
        print("logging customer reservation")
        response = reservation_table.put_item(
          Item=item
        )
        
        ui_response = f"We have reserved a {detail_data['unicorn_type'] if detail_data['penpal_type'] == 'Unicorn' else detail_data['puppy_type']} penpal for you!  Write them today at {detail_data['penpal_email']}. Your new bestie can't wait to hear from you."
        print(f"PutItem succeeded: {json.dumps(response, indent=4)}")
        return {
            'statusCode': 200,
            'headers': {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-store"
            },
            'body': json.dumps(ui_response)
        }
    
    except Exception as e:
        print(f"Error adding reservation to the table: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-store"
            },
            'body': json.dumps('Error adding penpal reservation.')
        }
