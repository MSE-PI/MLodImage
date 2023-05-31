#!/bin/bash

cd $REPO_ROOT

# Substitute the environment variables in the .dvc/config file

(cd code/models/genre_detector/ && dvc pull train)

cp code/models/genre_detector/src/model/* code/services/genre-detection/model/

cp code/models/genre_detector/params.yaml code/services/genre-detection/params.yaml

envsubst < .dvc/config > .dvc/config.local