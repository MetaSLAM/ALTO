import argparse
from pathlib import Path
from typing import Dict, List

import boto3
from botocore import UNSIGNED
from botocore.client import Config

# S3 configuration
BUCKET_NAME = "ALTO"
ENDPOINT_URL = "https://airlab-cloud.andrew.cmu.edu:8080/swift/v1/AUTH_ac8533a83cff4d48bc8c608ad222d330"
PREFIX_CHOICES = ["query", "reference"]

# Hardcoded dataset file lists
DATASET_FILES: Dict[str, List[str]] = {
    "query": [
        "query/FLT546_extracted_noGE_split.z01",
        "query/FLT546_extracted_noGE_split.z02",
        "query/FLT546_extracted_noGE_split.z03",
        "query/FLT546_extracted_noGE_split.z04",
        "query/FLT546_extracted_noGE_split.z05",
        "query/FLT546_extracted_noGE_split.z06",
        "query/FLT546_extracted_noGE_split.z07",
        "query/FLT546_extracted_noGE_split.z08",
        "query/FLT546_extracted_noGE_split.z09",
        "query/FLT546_extracted_noGE_split.z10",
        "query/FLT546_extracted_noGE_split.z11",
        "query/FLT546_extracted_noGE_split.z12",
        "query/FLT546_extracted_noGE_split.z13",
        "query/FLT546_extracted_noGE_split.z14",
        "query/FLT546_extracted_noGE_split.z15",
        "query/FLT546_extracted_noGE_split.z16",
        "query/FLT546_extracted_noGE_split.z17",
        "query/FLT546_extracted_noGE_split.z18",
        "query/FLT546_extracted_noGE_split.zip",
    ],
    "reference": [
        "reference/ge_images_split.z01",
        "reference/ge_images_split.z02",
        "reference/ge_images_split.z03",
        "reference/ge_images_split.z04",
        "reference/ge_images_split.z05",
        "reference/ge_images_split.z06",
        "reference/ge_images_split.z07",
        "reference/ge_images_split.z08",
        "reference/ge_images_split.z09",
        "reference/ge_images_split.zip",
    ],
}


class ALTODownloader:
    def __init__(self) -> None:
        self.client = boto3.client(
            "s3",
            endpoint_url=ENDPOINT_URL,
            config=Config(
                signature_version=UNSIGNED,
                s3={"addressing_style": "path"},
            ),
        )

    def download_files(self, keys: List[str], output_dir: Path, overwrite: bool = False) -> None:
        if not keys:
            print("No files configured for download.")
            return

        print(f"Found {len(keys)} files to download")

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
            f"Finished | downloaded: {downloaded}, skipped: {skipped}, failed: {failed}"
        )

    def download_subset(self, subset: str, output_dir: Path, overwrite: bool = False) -> None:
        keys = DATASET_FILES[subset]
        self.download_files(keys, output_dir, overwrite=overwrite)


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
        downloader.download_subset(subset, output_dir, overwrite=args.overwrite)


if __name__ == "__main__":
    main()