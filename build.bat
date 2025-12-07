@echo off
REM Build script for local testing (Windows version of build.sh)

echo Starting build process...

echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements\base.txt

echo Collecting static files...
python manage.py collectstatic --no-input

echo Running migrations...
python manage.py migrate --no-input

echo Build completed successfully!
