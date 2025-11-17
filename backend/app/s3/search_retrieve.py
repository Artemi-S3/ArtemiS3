import argparse
from pathlib import Path
from s3 import parse_s3_uri, get_public_client

def main() -> None:
    """
    CLI tool to demonstrate FR1 prototype.
    
    Usage
    -----
    >>> # get first 5 files from bucket
    >>> python search_retrieve.py s3://<NASA_bucket>/Mars --limit 5
    >>> # get first 3 files from bucket with '.pdf' file extension
    >>> python search_retrieve.py s3://<NASA_bucket>/Mars --contains .pdf --limit 3
    >>> # download first three files from bucket that contain 'Geology/year-' in their filepath to a './downloads'
    >>> python search_retrieve.py s3://<NASA_bucket>/Mars --contains Geology/year- --limit 3 --download-dir ./downloads
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("s3_uri", 
                    help="s3://<bucket>/<prefix>")
    ap.add_argument("--contains", 
                    default=None, 
                    help="substring filter, case sensitive")
    ap.add_argument("--limit", 
                    type=int,  
                    default=10, 
                    help="max results to print or download")
    ap.add_argument("--download-dir", 
                    default=None, 
                    help="if set, download up to <limit> files here")
    args = ap.parse_args()

    bucket, prefix = parse_s3_uri(args.s3_uri)
    s3 = get_public_client()

    pager = s3.get_paginator("list_objects_v2")
    printed = 0
    for page in pager.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if args.contains and args.contains not in key:
                continue
            print(f"{key}: {obj['Size']} bytes")
            if args.download_dir:
                out = Path(args.download_dir) / Path(key).name
                out.parent.mkdir(parents=True, exist_ok=True)
                s3.download_file(bucket, key, str(out))
                print(f"Saved files to '{out}'")
            printed += 1
            if printed >= args.limit:
                return
            
if __name__ == "__main__":
    main()
