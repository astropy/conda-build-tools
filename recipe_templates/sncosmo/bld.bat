"%PYTHON%" setup.py install --single-version-externally-managed --record=%TEMP%\record.txt
if errorlevel 1 exit 1

:: See https://groups.google.com/a/continuum.io/d/msg/conda/ZKdP5BujriA/55Y3L3eot5QJ
:: for reason for the options above. Can't use --offline because astropy_helpers
:: is not bundled.

:: Add more build steps here, if they are necessary.

:: See
:: http://docs.continuum.io/conda/build.html
:: for a list of environment variables that are set during the build process.
