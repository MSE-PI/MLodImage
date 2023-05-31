#!/bin/bash

cd $REPO_ROOT

# Substitute the environment variables in the .dvc/config file

dvc pull train

cp code/models/genre-detection/model.ckpt code/services/genre-detection/model/

cp code/models/genre-detection/src/* code/services/genre-detection/model/