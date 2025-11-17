import re
import boto3
from botocore import UNSIGNED
from botocore.client import Config
from mypy_boto3_s3 import S3Client
from typing import Optional, Tuple

def get_public_client(region: Optional[str] = None) -> S3Client:
    return boto3.client("s3", region_name=region, 
                        config=Config(signature_version=UNSIGNED))

def parse_s3_uri(uri: str) -> Tuple[str, ...]:
    match_ = re.match(r"^s3://([^/]+)(?:/(.*))?$", uri)
    if not match_:
        raise ValueError(f"Invalid S3 URI: {uri}")
    return match_.group(1), match_.group(2) or ""

def list_public(uri: str) -> None:
    sep_uri = parse_s3_uri(uri)  
    bucket, prefix = sep_uri
    s3 = get_public_client()
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            print(obj["Key"], obj["Size"])

def read_public_bytes(uri: str) -> bytes:
    bucket, prefix = parse_s3_uri(uri)
    s3 = get_public_client()
    return s3.get_object(Bucket=bucket, Key=prefix)["Body"].read()

def download_public(uri: str, dest: str) -> None:
    bucket, prefix = parse_s3_uri(uri)
    s3 = get_public_client()
    s3.download_file(bucket, prefix, dest)

if __name__ == "__main__":
    # not sure if this should be in .env or not since bucket is public 
    # (leaning towards yes)
    list_public("<s3_uri>")