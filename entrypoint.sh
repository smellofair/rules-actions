#!/bin/sh -l

HUB=$1;
REPO_LANG=${GITHUB_REPOSITORY:-2}

echo "Cloning $HUB... to update $REPO_LANG";
git clone git@github.com:$HUB hub-working-dir;

