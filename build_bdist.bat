set CONDA_LOC=C:\Users\mcraig\AppData\Local\Continuum\Anaconda\Scripts\
set CMD_IN_ENV=cmd /E:ON /V:ON /C %CONDA_LOC%obvci_appveyor_python_build_env.cmd

conda config --add channels astropy
python affiliate-builder\build_recipes.py

for /F "tokens=*" %%A in (.\build_order.txt) do (
	cd bdist_conda\%%A
	python setup.py bdist_conda
	cd ..\..
	)
