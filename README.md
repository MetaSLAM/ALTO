# ALTO (Aerial-view Large-scale Terrain-Oriented) dataset
Repository for the ALTO dataset for deep learning based UAV visual place recognition and localization tasks.


## Competition Dataset (GPR-Competition) for ICRA 2022
Download the 2022 GPR Competition datasets:

* The ROUND 1 dataset is available here: [Dropbox](https://www.dropbox.com/sh/q1w5dmghbkut553/AAAOCMaELmfHE4NN5cw06QBba?dl=0)

* The ROUND 2 dataset is available here: [Dropbox](https://www.dropbox.com/scl/fo/saejbf9qanbfq40k8jo18/h?dl=0&rlkey=l19kx1vzzahifv3n5lkg19n84)


## Full Dataset
Included is a simple Python script to download the **Full ALTO dataset** from an S3-compatible storage endpoint.

The script allows downloading specific subsets of the dataset (`query`, `reference`) or the full dataset.

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

Download the query subset:
```bash
python download_dataset.py --subset query --output-dir your/local/data/folder/
```

Download the reference subset:
```bash
python download_dataset.py --subset reference --output-dir your/local/data/folder/
```

Download all subsets:
```bash
python download_dataset.py --subset all --output-dir your/local/data/folder/
```


### Dataset Structure in S3

```text
s3://ALTO/
├── query/
│   ├── FLT546_extracted_noGE_split.z01
│   ├── FLT546_extracted_noGE_split.z02
│   ├── FLT546_extracted_noGE_split.z03
│   ├── ...
│   └── FLT546_extracted_noGE_split.zip
│
└── reference/
    ├── ge_images_split.z01
    ├── ge_images_split.z02
    ├── ge_images_split.z03
    ├── ...
    └── ge_images_split.zip
```

Each subset consists of a split ZIP archive. After downloading all parts (.z01, .z02, ..., .zip), the archive can be extracted normally:
```bash
unzip ge_images_split.zip
```

**All split files must be present in the same directory for extraction to work correctly.**


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
