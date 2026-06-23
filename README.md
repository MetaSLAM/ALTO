# ALTO (Aerial-view Large-scale Terrain-Oriented) dataset
Repository for the ALTO dataset for deep learning based UAV visual place recognition and localization tasks.

ALTO consists of two long (~150 km and ~260 km) trajectories flown by helicopter over
Ohio and Pennsylvania, with high-precision GPS ground truth, IMU readings, laser
altimeter readings, and a downward-facing RGB camera, together with georeferenced
satellite/aerial reference imagery over the flight paths.


## Full Dataset

The full dataset is now publicly available on the AirLab object store and can be
downloaded anonymously (no credentials or account required).

### Quick start

Requires Python 3 and `boto3` (`pip install boto3`). Then just run:

```bash
python download.py
```

Downloads all 29 files (~280 GiB) into `query/` and `reference/` folders here: `query/`
is 19 volumes (`.z01`...`.z18` plus `.zip`), `reference/` is 10 (`.z01`...`.z09` plus
`.zip`). It fetches a few files in parallel and is resumable — re-run it to skip finished
files and continue partial ones.

### Extracting the archives

Each part is a split (multi-volume) zip. Extract it with
[7-Zip](https://www.7-zip.org/): point it at the `.zip` and it pulls in the `.zXX` volumes
automatically (keep them in one folder).

```bash
7z x query/FLT546_extracted_noGE_split.zip
7z x reference/ge_images_split.zip
```

7-Zip is free on every OS — Windows (`winget install 7zip.7zip`), macOS
(`brew install sevenzip`), Linux (`apt install p7zip-full`).

> The built-in unzip can't open split `.z01` archives — use 7-Zip.


## Competition Dataset (GPR-Competition) for ICRA 2022
Download the 2022 GPR Competition datasets:

* The ROUND 1 dataset is available here: [Dropbox](https://www.dropbox.com/sh/q1w5dmghbkut553/AAAOCMaELmfHE4NN5cw06QBba?dl=0)

* The ROUND 2 dataset is available here: [Dropbox](https://www.dropbox.com/scl/fo/saejbf9qanbfq40k8jo18/h?dl=0&rlkey=l19kx1vzzahifv3n5lkg19n84)


## Cite
```
@inproceedings{cisneros2022alto,
  title     = {ALTO: A Large-Scale Dataset for UAV Visual Place Recognition and Localization},
  author    = {Cisneros, Ivan and Yin, Peng and Zhang, Ji and Choset, Howie and Scherer, Sebastian},
  booktitle = {arXiv preprint arXiv:2207.12317},
  year      = {2022}
}
```
