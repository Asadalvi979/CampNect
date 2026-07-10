cd CampNect_Backend
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn CampNect_Backend.wsgi --bind 0.0.0.0:$PORT
