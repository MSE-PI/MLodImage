#!/bin/bash

cd $REPO_ROOT

# Substitute the environment variables in the .dvc/config file

dvc pull train

cp code/models/genre_detector/model.ckpt code/services/genre-detection/model/

cp code/models/genre_detector/src/* code/services/genre-detection/model/

envsubst < .dvc/config > .dvc/config.local