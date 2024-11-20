import boto3
import os
import json
from botocore.exceptions import ClientError

BUCKET_NAME = os.getenv('WEB_ASSET_BUCKET')

s3_client = boto3.client('s3')

def lambda_handler(event, context):
    print(f"got event {event}")
    
    try: 
        # List objects in the bucket
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)
        objects = response.get('Contents', [])
        
        # Generate presigned URLs
        presigned_urls = []
        for obj in objects:
            if "ENCRYPTED" not in obj['Key'] and "ransom" not in obj['Key'] and "png" in obj['Key']:
                presigned_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': BUCKET_NAME, 'Key': obj['Key']},
                    ExpiresIn=43200  # 12 hour expiration
                )
                presigned_urls.append(presigned_url)

        return {
            'statusCode': 200,
            'headers': {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-store"
            },
            'body': json.dumps({'presignedUrls': presigned_urls})
        }
    except ClientError as e:
        print(e)
        
        return {
            'statusCode': 500,
            'headers': {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-store"
            },
            'body': json.dumps({"Message": "Internal Server error"})
        }
