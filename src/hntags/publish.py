import boto3
import os
import uuid
from os import walk


def push_files(bucket_name: str):
    s3 = boto3.resource("s3")

    generated_output_path = f"{os.getcwd()}/output"
    filenames = next(walk(generated_output_path), (None, None, []))[2]
    for filename in filenames:
        full_path = f"{os.getcwd()}/output/{filename}"
        print(f"Push file: '{full_path}' to bucket as '{filename}'")
        with open(full_path, "rb") as data:
            s3.Bucket(bucket_name).put_object(
                Key=filename, Body=data, ContentType="text/html;charset=utf-8"
            )


def create_invalidation(distribution_id: str):
    invalidation_uuid = str(uuid.uuid4())
    print(f"Creating invalidation with reference {invalidation_uuid}")
    cloudfront_client: boto3.CloudFront.Client = boto3.client("cloudfront")
    response = cloudfront_client.create_invalidation(
        DistributionId=distribution_id,
        InvalidationBatch={
            "Paths": {
                "Quantity": 1,
                "Items": [
                    "/*",
                ],
            },
            "CallerReference": invalidation_uuid,
        },
    )
    print(f"Invalidation response: {response}")


def publish(bucket_name: str, distribution_id: str):
    push_files(bucket_name)
    create_invalidation(distribution_id)
