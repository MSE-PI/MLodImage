#!/bin/bash
git clone -b develop https://$GIT_USER:$GIT_PASSWORD@github.com/MSE-PI/MLodImage.git app
git config --global credential.helper store