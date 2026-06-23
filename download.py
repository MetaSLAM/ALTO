"""Download the full ALTO dataset from the AirLab public object store.

Just run it:

    python download.py

It downloads everything (~280 GiB) into the current folder, as query/ and
reference/ subfolders. Files are fetched a few at a time in parallel, which is
much faster than one at a time because the server caps the speed of each
connection.

The download is resumable: finished files are skipped and a partly-downloaded
file continues from where it left off, so it is safe to stop (Ctrl-C) and re-run,
or to lose your connection mid-download. No credentials needed; the bucket is
public.
"""

import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import boto3
from botocore import UNSIGNED
from botocore.client import Config

ENDPOINT_URL = (
    "https://airlab-cloud.andrew.cmu.edu:8080/swift/v1/"
    "AUTH_ac8533a83cff4d48bc8c608ad222d330"
)
BUCKET_NAME = "ALTO"
OUTPUT_DIR = "."   # writes ./query/... and ./reference/... here
WORKERS = 4        # parallel downloads. The server caps each connection, so a
                   # few at once is ~3x faster. Raise it if your link is fast.
MAX_RETRIES = 20   # per file, across dropped connections

FILES = (
    [f"query/FLT546_extracted_noGE_split.z{i:02d}" for i in range(1, 19)]
    + ["query/FLT546_extracted_noGE_split.zip"]
    + [f"reference/ge_images_split.z{i:02d}" for i in range(1, 10)]
    + ["reference/ge_images_split.zip"]
)

# The connection pool must be at least as large as the number of workers.
client = boto3.client(
    "s3",
    endpoint_url=ENDPOINT_URL,
    config=Config(signature_version=UNSIGNED, max_pool_connections=WORKERS + 2),
)

_lock = threading.Lock()
_done_bytes = 0
_total_bytes = 0


def _progress(delta):
    """Add to the shared byte counter and redraw one aggregate progress line."""
    global _done_bytes
    with _lock:
        _done_bytes += delta
        pct = _done_bytes / _total_bytes * 100 if _total_bytes else 100.0
        sys.stdout.write(
            f"\r  {pct:5.1f}%   {_done_bytes / 1024**3:7.2f} / "
            f"{_total_bytes / 1024**3:.2f} GiB"
        )
        sys.stdout.flush()


def download(key, size):
    """Download one object, resuming from whatever is already on disk."""
    target = os.path.join(OUTPUT_DIR, key)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    for attempt in range(1, MAX_RETRIES + 1):
        have = os.path.getsize(target) if os.path.isfile(target) else 0
        if have >= size:
            return
        try:
            kw = {"Bucket": BUCKET_NAME, "Key": key}
            if have:
                kw["Range"] = f"bytes={have}-"  # resume
            resp = client.get_object(**kw)
            with open(target, "ab" if have else "wb") as f:
                for chunk in resp["Body"].iter_chunks(chunk_size=8 * 1024 * 1024):
                    f.write(chunk)
                    _progress(len(chunk))
            return
        except Exception as e:  # connection dropped, timeout, etc. -> resume
            wait = min(60, 5 * attempt)
            sys.stdout.write(
                f"\n  ! {key}: interrupted ({type(e).__name__}); "
                f"retry {attempt}/{MAX_RETRIES} in {wait}s\n"
            )
            time.sleep(wait)
    raise RuntimeError(f"gave up on {key} after {MAX_RETRIES} attempts")


print("Checking what is already on disk...")
sizes = {k: client.head_object(Bucket=BUCKET_NAME, Key=k)["ContentLength"] for k in FILES}
_total_bytes = sum(sizes.values())
for k in FILES:
    p = os.path.join(OUTPUT_DIR, k)
    if os.path.isfile(p):
        _done_bytes += min(os.path.getsize(p), sizes[k])
todo = [k for k in FILES if not (
    os.path.isfile(os.path.join(OUTPUT_DIR, k))
    and os.path.getsize(os.path.join(OUTPUT_DIR, k)) == sizes[k]
)]

print(
    f"{_total_bytes / 1024**3:.1f} GiB total, "
    f"{_done_bytes / 1024**3:.1f} GiB already here, "
    f"{len(todo)} of {len(FILES)} files left ({WORKERS} at a time).\n"
)

with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    list(ex.map(lambda k: download(k, sizes[k]), todo))

print("\nDone.")
