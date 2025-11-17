import json
from pathlib import Path
from typing import List, Dict
import sys


def get_current_files_from_mock(bucket_name: str) -> List[Dict]:

    path = Path(bucket_name)
    if not path.exists():
        raise FileNotFoundError(f"Bucket '{bucket_name}' not found.")

    with open(path, "r") as f:
        data = json.load(f)

    return data



def refresh_search_index(bucket_name: str, cache_file: str = "index_cache.json"):
    """
    FR6 Prototype Demonstration

    Usage
    -----
    >>> # Refresh bucket search index
    >>> python index_refresh.py <NASA_Bucket_Name>
    """
    
    current_files = get_current_files_from_mock(bucket_name)

    cache_path = Path(cache_file)
    if cache_path.exists():
        with open(cache_path, "r") as f:
            previous_files = json.load(f)
    else:
        previous_files = []

    prev_keys = {f["Key"] for f in previous_files}
    curr_keys = {f["Key"] for f in current_files}

    # Detect new and removed files
    new_files = [f for f in current_files if f["Key"] not in prev_keys]
    removed_files = [f for f in previous_files if f["Key"] not in curr_keys]

    # Simulate updating the search index
    if new_files:
        print(f"Found {len(new_files)} new files:")
        for f in new_files:
            print(f"  + {f['Key']} (size: {f['Size']} bytes)")
    else:
        print("No new files found.")

    print()

    if removed_files:
        print(f"{len(removed_files)} files removed:")
        for f in removed_files:
            print(f"  - {f['Key']} (size: {f['Size']} bytes)")
    else:
        print("No files removed.")

    # Save the new state to disk
    with open(cache_path, "w") as f:
        json.dump(current_files, f, indent=2)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python index_refresh.py <bucket_name>")
        sys.exit(1)

    bucket_name = sys.argv[1]
    refresh_search_index(bucket_name)
