"""
This file contains a script to check if the model needs to be retrained
"""

__author__ = "Florian Hofmann"
__date__ = "10.05.2023"

import os

FILES_TO_TRACK = ["src", "data.dvc", "dvc.yaml", "params.yaml"]


def get_modified_files() -> list:
    """
    This function returns a list of all files that have been modified in the last commit
    """
    # get list of modified files in the last commit
    modified_files = os.popen("git diff --name-only HEAD^ HEAD").read().split("\n")

    # filter for only models changes
    modified_files = list(filter(lambda x: x.startswith("code/services/"), modified_files))

    # keep only the service/frontend name
    modified_files = list(map(lambda x: x.split("/")[2], modified_files))

    # remove duplicates
    modified_files = list(set(modified_files))

    return modified_files


def main():
    modified_files = get_modified_files()

    for file in modified_files:
        if file in FILES_TO_TRACK:
            print("Model needs to be retrained")
            exit(1)

    print("Model does not need to be retrained")
    exit(0)


if __name__ == '__main__':
    main()
