"""
This python file as the objective to train the model and save it on DVC
"""
import os
from datetime import datetime

GIT_REPO: str = "https://github.com/MSE-PI/MLodImage.git"
BRANCH_NAME: str = os.environ["TRAIN_BRANCH"]
MINIO_USR: str = os.environ["MINIO_USR"]
MINIO_PWD: str = os.environ["MINIO_PWD"]


def main():
    # create a new branch
    os.system(f"git checkout -b {BRANCH_NAME}")
    # dvc pull, train model, test, ...
    # TODO
    print(BRANCH_NAME + " " + MINIO_USR + " " + MINIO_PWD)
    # commit and push changes
    now = datetime.now()
    os.system(f"git add . && git commit -m \"{now}: model train\"")
    os.system(f"git push --set-upstream origin {BRANCH_NAME}-{int(now.timestamp())}")


# entry point
if __name__ == '__main__':
    main()
