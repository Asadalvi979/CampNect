cd CampNect_Backend
python manage.py migrate --noinput || true
python manage.py collectstatic --noinput || true
gunicorn CampNect_Backend.wsgi --bind 0.0.0.0:$PORT
