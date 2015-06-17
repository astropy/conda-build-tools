conda config --add channels astropy
python affiliate-builder\build_recipes.py

for /F "tokens=*" %%A in (.\build_order.txt) do (
	cd bdist_conda\%%A
	python setup.py bdist_conda
	cd ..\..
	)
