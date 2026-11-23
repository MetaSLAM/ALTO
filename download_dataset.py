import argparse
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import boto3
from botocore import UNSIGNED
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

# S3 configuration
BUCKET_NAME = "ALTO"
ENDPOINT_URL = "https://airlab-cloud.andrew.cmu.edu:8080/swift/v1/AUTH_ac8533a83cff4d48bc8c608ad222d330"
PREFIX_CHOICES = ["query", "reference"]
CHUNK_SIZE = 8 * 1024 * 1024
MAX_RETRIES = 20
MAX_RETRY_DELAY_SECONDS = 60
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
RETRYABLE_ERROR_CODES = {
    "InternalError",
    "RequestTimeout",
    "RequestTimeoutException",
    "ServiceUnavailable",
    "SlowDown",
    "Throttling",
    "ThrottlingException",
}

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


class DownloadValidationError(Exception):
    """Raised when a server response cannot safely be written or resumed."""


class IncompleteDownloadError(Exception):
    """Raised when a response ends before the expected object size is reached."""


class ALTODownloader:
    def __init__(self, workers: int = 2) -> None:
        if workers < 1:
            raise ValueError("workers must be at least 1")

        self.workers = workers
        self.client = boto3.client(
            "s3",
            endpoint_url=ENDPOINT_URL,
            config=Config(
                signature_version=UNSIGNED,
                max_pool_connections=workers + 2,
                s3={"addressing_style": "path"},
            ),
        )
        self.done_bytes = 0
        self.total_bytes = 0
        self.progress_visible = False
        self.output_lock = threading.Lock()

    @staticmethod
    def _is_retryable(error: Exception) -> bool:
        if isinstance(error, ClientError):
            response = error.response
            status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            code = response.get("Error", {}).get("Code", "")
            return status in RETRYABLE_STATUS_CODES or code in RETRYABLE_ERROR_CODES

        return isinstance(error, (BotoCoreError, IncompleteDownloadError))

    @staticmethod
    def _retry_delay(attempt: int) -> int:
        return min(MAX_RETRY_DELAY_SECONDS, 5 * attempt)

    def _message(self, message: str) -> None:
        with self.output_lock:
            self._message_unlocked(message)

    def _message_unlocked(self, message: str) -> None:
        if self.progress_visible:
            sys.stdout.write("\n")
            self.progress_visible = False
        print(message)

    def _show_progress(self) -> None:
        with self.output_lock:
            self._show_progress_unlocked()

    def _show_progress_unlocked(self) -> None:
        percent = (
            self.done_bytes / self.total_bytes * 100 if self.total_bytes else 100.0
        )
        sys.stdout.write(
            f"\rOverall: {percent:5.1f}% | "
            f"{self.done_bytes / 1024**3:7.2f} / "
            f"{self.total_bytes / 1024**3:.2f} GiB"
        )
        sys.stdout.flush()
        self.progress_visible = True

    def _progress(self, delta: int) -> None:
        with self.output_lock:
            self.done_bytes += delta
            self._show_progress_unlocked()

    def _remote_size(self, key: str) -> Optional[int]:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.client.head_object(Bucket=BUCKET_NAME, Key=key)
                return response["ContentLength"]
            except Exception as error:
                if not self._is_retryable(error) or attempt == MAX_RETRIES:
                    self._message(f"Failed to read metadata for {key}: {error}")
                    return None

                delay = self._retry_delay(attempt)
                self._message(
                    f"Metadata request for {key} was interrupted "
                    f"({type(error).__name__}); retry {attempt}/{MAX_RETRIES} "
                    f"in {delay}s"
                )
                time.sleep(delay)

        return None

    @staticmethod
    def _prepare_partial_file(
        target: Path, partial: Path, size: int, overwrite: bool
    ) -> int:
        if overwrite:
            if partial.exists():
                partial.unlink()
            return 0

        if partial.is_file():
            partial_size = partial.stat().st_size
            if partial_size <= size:
                return partial_size
            partial.unlink()

        if target.is_file():
            target_size = target.stat().st_size
            if target_size < size:
                target.replace(partial)
                return target_size

        return 0

    def _download_file(self, key: str, size: int, partial: Path) -> bool:
        for attempt in range(1, MAX_RETRIES + 1):
            have = partial.stat().st_size if partial.is_file() else 0
            if have > size:
                self._message(
                    f"Failed to download {key}: partial file is larger than "
                    "the remote object"
                )
                return False
            if have == size:
                return True

            try:
                request = {"Bucket": BUCKET_NAME, "Key": key}
                if have:
                    request["Range"] = f"bytes={have}-"

                response = self.client.get_object(**request)
                body = response["Body"]

                if have:
                    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
                    content_range = response.get("ContentRange", "")
                    if status != 206 or not content_range.startswith(f"bytes {have}-"):
                        body.close()
                        raise DownloadValidationError(
                            "the server did not honor the requested byte range"
                        )

                expected_length = size - have
                content_length = response.get("ContentLength")
                if content_length is not None and content_length != expected_length:
                    body.close()
                    raise DownloadValidationError(
                        "the remote object size changed during the download"
                    )

                try:
                    with partial.open("ab" if have else "wb") as output:
                        for chunk in body.iter_chunks(chunk_size=CHUNK_SIZE):
                            if chunk:
                                output.write(chunk)
                                self._progress(len(chunk))
                finally:
                    body.close()

                actual_size = partial.stat().st_size
                if actual_size != size:
                    raise IncompleteDownloadError(
                        f"received {actual_size} of {size} bytes"
                    )
                return True
            except Exception as error:
                if not self._is_retryable(error) or attempt == MAX_RETRIES:
                    self._message(f"Failed to download {key}: {error}")
                    return False

                delay = self._retry_delay(attempt)
                self._message(
                    f"Download of {key} was interrupted "
                    f"({type(error).__name__}); retry {attempt}/{MAX_RETRIES} "
                    f"in {delay}s"
                )
                time.sleep(delay)

        return False

    def _download_and_finalize(
        self,
        position: int,
        total: int,
        key: str,
        size: int,
        target: Path,
        partial: Path,
    ) -> bool:
        self._message(f"[{position}/{total}] Downloading {key}")

        if not self._download_file(key, size, partial):
            return False

        try:
            partial.replace(target)
        except OSError as error:
            self._message(f"[{position}/{total}] Failed to save {target}: {error}")
            return False

        self._message(f"[{position}/{total}] Saved to {target}")
        return True

    def download_files(
        self, keys: List[str], output_dir: Path, overwrite: bool = False
    ) -> None:
        if not keys:
            print("No files configured for download.")
            return

        print(f"Checking remote sizes for {len(keys)} files...")
        sizes: Dict[str, int] = {}
        metadata_failures = 0
        for key in keys:
            size = self._remote_size(key)
            if size is None:
                metadata_failures += 1
            else:
                sizes[key] = size

        downloaded = 0
        skipped = 0
        failed = metadata_failures
        pending: List[Tuple[str, int, Path, Path]] = []

        self.total_bytes = sum(sizes.values())
        self.done_bytes = 0

        for key, size in sizes.items():
            target = output_dir / key
            partial = target.with_name(f"{target.name}.part")
            target.parent.mkdir(parents=True, exist_ok=True)

            if target.is_file() and target.stat().st_size == size and not overwrite:
                self.done_bytes += size
                skipped += 1
                continue

            try:
                have = self._prepare_partial_file(target, partial, size, overwrite)
            except OSError as error:
                self._message(f"Failed to prepare {target}: {error}")
                failed += 1
                continue

            self.done_bytes += have
            pending.append((key, size, target, partial))

        print(
            f"{self.total_bytes / 1024**3:.1f} GiB total, "
            f"{self.done_bytes / 1024**3:.1f} GiB already present, "
            f"{len(pending)} of {len(sizes)} available files remaining "
            f"({self.workers} worker{'s' if self.workers != 1 else ''})."
        )
        self._show_progress()

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {
                executor.submit(
                    self._download_and_finalize,
                    position,
                    len(pending),
                    key,
                    size,
                    target,
                    partial,
                ): key
                for position, (key, size, target, partial) in enumerate(
                    pending, start=1
                )
            }

            for future in as_completed(futures):
                key = futures[future]
                try:
                    if future.result():
                        downloaded += 1
                    else:
                        failed += 1
                except Exception as error:
                    self._message(f"Failed to download {key}: {error}")
                    failed += 1

        self._message(
            f"Finished | downloaded: {downloaded}, skipped: {skipped}, failed: {failed}"
        )

    def download_subset(self, subset: str, output_dir: Path, overwrite: bool = False) -> None:
        keys = DATASET_FILES[subset]
        self.download_files(keys, output_dir, overwrite=overwrite)


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error

    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


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

    parser.add_argument(
        "--workers",
        type=positive_int,
        default=2,
        help="Number of files to download concurrently (default: 2).",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    downloader = ALTODownloader(workers=args.workers)
    output_dir = Path(args.output_dir)

    subsets = PREFIX_CHOICES if args.subset == "all" else [args.subset]

    keys = [key for subset in subsets for key in DATASET_FILES[subset]]
    print(f"Downloading subset{'s' if len(subsets) > 1 else ''}: {', '.join(subsets)}")
    downloader.download_files(keys, output_dir, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
