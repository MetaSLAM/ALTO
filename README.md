# ALTO (Aerial-view Large-scale Terrain-Oriented) dataset
Repository for the ALTO dataset for deep learning based UAV visual place recognition and localization tasks.


## Competition Dataset (GPR-Competition) for ICRA 2022
Download the 2022 GPR Competition datasets:

* The ROUND 1 dataset is available here: [Dropbox](https://www.dropbox.com/sh/q1w5dmghbkut553/AAAOCMaELmfHE4NN5cw06QBba?dl=0)

* The ROUND 2 dataset is available here: [Dropbox](https://www.dropbox.com/scl/fo/saejbf9qanbfq40k8jo18/h?dl=0&rlkey=l19kx1vzzahifv3n5lkg19n84)


## Full Dataset
Included is a Python script to download the **Full ALTO dataset** from an S3-compatible storage endpoint.

The script can download the `query`, `reference`, or `metadata` subset individually, or download all three together. Downloads are resumable and do not require AWS credentials because the dataset objects are publicly readable.

### Installation

We recommend using **Python 3.10** or newer.

Create a virtual environment (optional but recommended):

```bash
python -m venv alto-env
source alto-env/bin/activate
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Running the Downloader

The general command is:

```bash
python download_dataset.py --subset SUBSET --output-dir OUTPUT_DIR [--workers N] [--overwrite]
```

For example, download the query subset:

```bash
python download_dataset.py --subset query --output-dir your/local/data/folder/
```

Download the reference subset:

```bash
python download_dataset.py --subset reference --output-dir your/local/data/folder/
```

Download only the camera metadata:

```bash
python download_dataset.py --subset metadata --output-dir your/local/data/folder/
```

Download the query, reference, and metadata subsets together:

```bash
python download_dataset.py --subset all --output-dir your/local/data/folder/
```

The downloader preserves the S3 directory structure beneath the output directory. For example, `--subset metadata --output-dir ./data` writes the files under `./data/metadata/`.

#### Command-line options

| Option | Required | Default | Description |
|---|---|---|---|
| `--subset {query,reference,metadata,all}` | Yes | No default | Selects one dataset subset, or `all` to download every subset. |
| `--output-dir PATH` | Yes | No default | Sets the local root directory. Subset directories are created inside it as needed. |
| `--workers N` | No | `2` | Sets the number of files downloaded concurrently. `N` must be at least 1. |
| `--overwrite` | No | Off | Restarts each selected file from the beginning and replaces an existing local copy. |

Without `--overwrite`, a completed local file with the expected remote size is skipped. An incomplete download is stored with a `.part` suffix and resumed the next time the same command is run. Run `python download_dataset.py --help` to see the options in the terminal.


### Dataset Structure in S3

```text
s3://ALTO/
├── query/
│   ├── FLT546_extracted_noGE_split.z01
│   ├── FLT546_extracted_noGE_split.z02
│   ├── FLT546_extracted_noGE_split.z03
│   ├── ...
│   └── FLT546_extracted_noGE_split.zip
├── reference/
│   ├── ge_images_split.z01
│   ├── ge_images_split.z02
│   ├── ge_images_split.z03
│   ├── ...
│   └── ge_images_split.zip
└── metadata/
    ├── README.md
    ├── camera.yaml
    └── image_camera_poses.csv
```

The `query` and `reference` subsets each consist of a split ZIP archive. After downloading all parts (`.z01`, `.z02`, ..., `.zip`), the archive can be extracted normally:

```bash
unzip ge_images_split.zip
```

**All split files must be present in the same directory for extraction to work correctly.**

### Camera Metadata

The `metadata/` directory relates each downward-facing query image to an Earth-fixed camera pose. It supports camera stabilization, nadir-view generation, and other geometric processing without requiring ROS or the original bag files.

- `metadata/camera.yaml` contains the 1600x1200 pinhole-camera calibration, lens distortion parameters, coordinate conventions, and the fixed INS-to-optical-camera transform.
- `metadata/image_camera_poses.csv` contains one WGS 84 ECEF optical-camera pose and smoothed above-ground altitude value per image. Image paths are relative to the dataset image root.
- [`metadata/README.md`](metadata/README.md) documents the frame chain, quaternion convention, coordinate system, and every CSV column in detail.


## Cite
If you use this dataset in your research, please cite:

Paper: [arXiv](https://arxiv.org/abs/2207.12317)

```bibtex
@article{cisneros2022alto,
  title = {ALTO: A Large-Scale Dataset for UAV Visual Place Recognition and Localization},
  author = {Cisneros, Ivan and Yin, Peng and Zhang, Ji and Choset, Howie and Scherer, Sebastian},
  journal = {arXiv preprint arXiv:2207.12317},
  year = {2022}
}
```
