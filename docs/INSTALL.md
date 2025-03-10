## Installation

### Requirements

- Linux (Windows is not officially supported)
- Python 3.5+ (Python 2 is not supported)
- PyTorch 1.1 or higher
- CUDA 9.0 or higher
- NCCL 2
- GCC(G++) 4.9 or higher
- [mmcv](https://github.com/open-mmlab/mmcv)

We have tested the following versions of OS and softwares:

- OS: Ubuntu 16.04/18.04 and CentOS 7.2
- CUDA: 9.0/9.2/10.0
- NCCL: 2.1.15/2.2.13/2.3.7/2.4.2
- GCC(G++): 4.9/5.3/5.4/7.3

### Install mmdetection

a. Create a conda virtual environment and activate it.

```shell
conda create -n MRDet python=3.7 -y
conda activate MRDet
```

b. Install PyTorch stable or nightly and torchvision following the [official instructions](https://pytorch.org/), e.g.,

```shell
conda install pytorch torchvision -c pytorch
```

c. Clone the mmdetection repository.

```shell
git clone https://github.com/qinr/MRDet.git
cd MRDet
```

d. Install mmdetection (other dependencies will be installed automatically).

```shell
pip install mmcv
python setup.py develop  # or "pip install -v -e ."
```

Note:

1. The git commit id will be written to the version number with step d, e.g. 0.6.0+2e7045c. The version will also be saved in trained models.
It is recommended that you run step d each time you pull some updates from github. If C/CUDA codes are modified, then this step is compulsory.

2. Following the above instructions, mmdetection is installed on `dev` mode, any local modifications made to the code will take effect without the need to reinstall it (unless you submit some commits and want to update the version number).

3. If you would like to use `opencv-python-headless` instead of `opencv-python`,
you can install it before installing MMCV.

### Another option: Docker Image

We provide a [Dockerfile](../docker/Dockerfile) to build an image.

```shell
# build an image with PyTorch 1.1, CUDA 10.0 and CUDNN 7.5
docker build -t mmdetection docker/
```

### Prepare datasets

It is recommended to symlink the dataset root to `$MMDETECTION/data`.
If your folder structure is different, you may need to change the corresponding paths in config files.

```
mmdetection
├── mmdet
├── tools
├── configs
├── data
│   ├── DOTA
│   │   ├── trainval1024
|   |   |          ├── DOTA_trainval1024.json
|   |   |          ├── images
|   |   |          ├── labelTxt
│   │   ├── test1024
|   |   |          ├── DOTA_test1024.json
|   |   |          ├── images
```

The DOTA images and labels have to be splitted using the code [here](https://github.com/CAPTAIN-WHU/DOTA_devkit). You can also use the scripts in DOTA_devkit/prepare_dota1.py to obtain the splitted dataset. If you use codes in DOTA_devkit/, you need to install packages following https://github.com/CAPTAIN-WHU/DOTA_devkit. The DOTA annotations should be converted into the coco format using the scripts in DOTA_devkit/DOTA2COCO.py.


### Multiple versions

If there are more than one mmdetection on your machine, and you want to use them alternatively, the recommended way is to create multiple conda environments and use different environments for different versions.

Another way is to insert the following code to the main scripts (`train.py`, `test.py` or any other scripts you run)
```python
import os.path as osp
import sys
sys.path.insert(0, osp.join(osp.dirname(osp.abspath(__file__)), '../'))
```
or run the following command in the terminal of corresponding folder.
```shell
export PYTHONPATH=`pwd`:$PYTHONPATH
```
