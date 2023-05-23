#!/bin/bash

# CLONE AND PULL DATA
git clone -b develop https://$GIT_USER:$GIT_PASSWORD@github.com/MSE-PI/MLodImage.git app
sleep 2  # wait 2 second to be sure that the clone is done and the branch is checked out
git config --global credential.helper store
cd app
git checkout -b $BRANCH_NAME
envsubst < .dvc/config > .dvc/config.local
dvc pull

# EXPERIMENT
cd code/models/genre_detector
dvc repro

# INDICATE RELATED SERVICE MUST BE REDEPLOYED
echo $(date +%s) > ../../services/genre-detection/last_training.txt

# COMMIT AND PUSH
cd /app
git add .
git commit -m "Training on $(date +'%D %T')"
git push origin $BRANCH_NAME