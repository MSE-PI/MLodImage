#!/bin/bash

# CLONE AND PULL DATA
git clone -b develop https://$GIT_USER:$GIT_PASSWORD@github.com/MSE-PI/MLodImage.git app
sleep 2  # wait 2 second to be sure that the clone is done and the branch is checked out
git config --global user.name "Train POD"
git config --global user.email "pod@train.mlodimage.ch"
cd app
git checkout $TRAIN_BRANCH
git merge develop --no-edit
envsubst < .dvc/config > .dvc/config.local

# EXPERIMENT
cd /app/code/models/genre_detector
dvc pull data
dvc repro
dvc push

# INDICATE RELATED SERVICE MUST BE REDEPLOYED
echo $(date +%s) > /app/code/services/genre-detection/last_training.txt

# COMMIT AND PUSH
cd /app
git add .
git commit -m "Training on $(date +'%D %T')"
git push https://$GIT_USER:$GIT_PASSWORD@github.com/MSE-PI/MLodImage.git $TRAIN_BRANCH
