import re
import boto3
from botocore import UNSIGNED
from botocore.client import Config
from mypy_boto3_s3 import S3Client
from typing import Optional

def parse_s3_uri(uri: str) -> tuple[str, str]:
    match_ = re.match(r"^s3://([^/]+)(?:/(.*))?$", uri)
    if not match_:
        raise ValueError(f"Invalid S3 URI: {uri}")
    return match_.group(1), match_.group(2) or ""

def get_public_client(region: Optional[str] = None) -> S3Client:
    return boto3.client("s3", region_name=region, 
                        config=Config(signature_version=UNSIGNED))
