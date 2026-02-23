#!/bin/bash

find -name '#*' -delete
find -name 'step*.pdb' -delete
rm -rf slurm_jobs/* > /dev/null 2>&1
# rm -rf tmp/* > /dev/null 2>&1
