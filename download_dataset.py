import argparse
from pathlib import Path
from typing import List

import boto3
from botocore import UNSIGNED
from botocore.client import Config

# S3 configuration
BUCKET_NAME = "ALTO"
ENDPOINT_URL = "https://airlab-cloud.andrew.cmu.edu:8080"
PREFIX_CHOICES = ["query", "reference"]


class ALTODownloader:
    def __init__(self) -> None:
        self.client = boto3.client(
            "s3",
            endpoint_url=ENDPOINT_URL,
            config=Config(signature_version=UNSIGNED),
        )

    def list_files(self, prefix: str) -> List[str]:
        paginator = self.client.get_paginator("list_objects_v2")
        keys: List[str] = []

        for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if not key.endswith("/"):
                    keys.append(key)

        return sorted(keys)

    def download_prefix(self, prefix: str, output_dir: Path, overwrite: bool = False) -> None:
        prefix = prefix.rstrip("/") + "/"
        keys = self.list_files(prefix)

        if not keys:
            print(f"No files found under prefix: {prefix}")
            return

        print(f"Found {len(keys)} files under {prefix}")

        downloaded = 0
        skipped = 0
        failed = 0

        for i, key in enumerate(keys, start=1):
            local_path = output_dir / key
            local_path.parent.mkdir(parents=True, exist_ok=True)

            if local_path.exists() and not overwrite:
                print(f"[{i}/{len(keys)}] Skipping existing file: {local_path}")
                skipped += 1
                continue

            print(f"[{i}/{len(keys)}] Downloading {key}")

            try:
                self.client.download_file(BUCKET_NAME, key, str(local_path))
                print(f"[{i}/{len(keys)}] Saved to {local_path}")
                downloaded += 1
            except Exception as e:
                print(f"[{i}/{len(keys)}] Failed to download {key}: {e}")
                failed += 1

        print(
            f"Finished {prefix} | downloaded: {downloaded}, skipped: {skipped}, failed: {failed}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download the ALTO dataset from S3"
    )

    parser.add_argument(
        "--subset",
        choices=PREFIX_CHOICES + ["all"],
        required=True,
        help="Dataset subset to download. Use 'all' to download all data.",
    )

    parser.add_argument(
        "--output-dir",
        required=True,
        help="Local output directory.",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files at the local download path.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    downloader = ALTODownloader()
    output_dir = Path(args.output_dir)

    subsets = PREFIX_CHOICES if args.subset == "all" else [args.subset]

    for subset in subsets:
        print(f"\nDownloading subset: {subset}")
        downloader.download_prefix(subset, output_dir, overwrite=args.overwrite)


if __name__ == "__main__":
    main()