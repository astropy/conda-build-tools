conda config --add channels astropy

for /F "tokens=*" %%A in (.\build_order.txt) do (
	cd bdist_conda\%%A
	python setup.py bdist_conda
	cd ..\..
	)
