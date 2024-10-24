# ArchiveTools
Set of tools for managing electronic archive files, written in Python.

Tools can be executed as : `archivetools <tool>`.


# Tools
Available tools are :
    - check, to check for invalid paths in a file system
    - copy, to copy the structure of a directory as only empty files

More information about each tool can be obtained by running `archivetools <tool> --help`


# Installation

## Recommended
The recommended installation uses pipx (https://pipx.pypa.io/stable/) to install the archivetools package in an 
isolated environment and create a shortcut to it in the console.

```shell
pipx install archivetools
archivetools --help
```

## Pip
From a Python environment :

```shell
pip install archivetools
archivetools --help
```

## From source
Clone the source code :

```
git clone git@github.com:MatteoBouvier/ArchiveTools.git
python -m archivetools --help
```
