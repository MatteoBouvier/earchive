# EArchive
Set of tools for managing electronic archive files, written in Python.

Tools can be executed as : `earchive <tool>`.


# Tools
Available tools are :
    - check, to check for invalid paths in a file system
    - copy, to copy the structure of a directory as only empty files
    - analyze, to get attributes of a directory

More information about each tool can be obtained by running `earchive <tool> --help`


# Installation

## Recommended
The recommended installation uses pipx (https://pipx.pypa.io/stable/) to install the earchive package in an 
isolated environment and create a shortcut to it in the console.

```shell
pipx install earchive
earchive --help
```

## Pip
From a Python environment :

```shell
pip install earchive
earchive --help
```

## From source
Clone the source code :

```
git clone git@github.com:MatteoBouvier/earchive.git
python -m earchive --help
```


# TODO:
- fs case sensitivity
- unicode PUA
