import numpy as np
import skimage.io
import paramiko
import frontmatter
import pandas as pd
import scp
import yaml
import os


def scrape_frontmatter(dirname, file='README.md', as_dataframe=False):
    """
    Reads the status of a given experimental dataset. This status is embedded
    in the README.md file as a YAML metadata block.

    Parameters
    ----------
    dirname : str
        Directory from which to parse.
    file: str
        Name of file containing YAML frontmatter. Default is 'README.md'
    as_dataframe : bool
        If True, yaml key and values will be returned as a pandas DataFrame.

    Returns
    -------
    info : dict or pandas DataFrame
        A dictionary or DataFrame with all frontmatter keys and values.

    Raises
    ------
    UserWarning
        A UserWarning is raised if the scraped yaml frontmatter does not have
        a 'status' key or the value is not in `['accepted', 'rejected',
        'questionable']`.
    """
    # Grab file from directory.
    if dirname[-1] == '/':
        filename = '{}{}'.format(dirname, file)
    else:
        filename = '{}/{}'.format(dirname, file)

    # Scrape and return as desired.
    with open(filename) as f:
        info, _ = frontmatter.parse(f.read())
    if 'status' not in info.keys():
        raise UserWarning("""key `status` not found in metadata keys.\n
                          skipping {}""".format(f.split('/')[-2]))
        info = {}
    elif info['status'].lower() not in ['accepted', 'questionable', 'rejected']:
        raise UserWarning("""Value `status: {}` not an acceptable flag. \n
                          Skipping {}""".format(f.split('/')[-2]))
        info = {}
    if as_dataframe == True:
        info = pd.DataFrame(info, index={0})
    return info


def pull_clist(src, username, port, dest):
    """
    Pulls the clist files from a target directory on delbrück to local.

    Parameters
    ----------
    src: str
        Source directory on Delbrück. This should be given as a relative path.
    dst: str
        Target directory on local. If None, the clists will be pulled into
        `data/images` with the same folder name.
    username: str
        Username to access the data.
    port : int
        Super secret Delbrück port number.
    """
    return True


def deoposit_data(src, dest, port, username):
    return True
