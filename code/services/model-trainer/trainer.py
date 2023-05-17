"""
This python file as the objective to train the model and save it on DVC
"""
import os
from datetime import datetime

GIT_REPO:str = "https://github.com/MSE-PI/MLodImage.git"
BRANCH_NAME: str = "train-model"

def main():
    # create a new branch
    os.system(f"git checkout -b {BRANCH_NAME}")
    # dvc pull, train model, test, ...
    # TODO
    with open('test.txt', 'w') as f:
        f.write('Create a new text file!')
    # commit and push changes
    now = datetime.now()
    date = now.strftime("%m/%d/%Y, %H:%M:%S")
    os.system(f"git add . && git commit -m \"{date}: model train\" && git push –set-upstream origin {BRANCH_NAME}")

# entry point
if __name__ == '__main__':
    main()