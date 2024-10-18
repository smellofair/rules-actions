#!/bin/bash

echo "This is a test";
echo "Args: $1";
env >> $GITHUB_OUTPUT;
pwd >> $GITHUB_OUTPUT;
ls >> $GITHUB_OUTPUT;
