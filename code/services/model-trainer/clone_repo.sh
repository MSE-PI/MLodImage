#!/bin/bash
git clone -b develop https://$GIT_USER:$GIT_PASSWORD@github.com/MSE-PI/MLodImage.git app
git config --global credential.helper store
sleep 5  # wait 5 second to be sure that the clone is done and the branch is checked out