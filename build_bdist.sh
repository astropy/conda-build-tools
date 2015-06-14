#! /bin/bash

base=$PWD

# Script below uses obvious-ci to build AND UPLOAD the packages with recipes.
python affiliate-builder/build_recipes.py

to_build=$(cat build_order.txt)
cd bdist_conda
for d in $to_build
    do
        cd $d
        python setup.py bdist_conda || echo "Failed on $PWD"
        cd ..
    done

cd $base

