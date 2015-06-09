#! /bin/bash

base=$PWD


to_build_recipe=recipes/[a-z]*
for recipe in $to_build_recipe
do
    CONDA_PY=2.7 conda build $recipe || echo "Failed on $recipe"
done

to_build=$(cat build_order.txt)
cd bdist_conda
for d in $to_build
    do
        cd $d
        python setup.py bdist_conda || echo "Failed on $PWD"
        cd ..
    done

cd $base

