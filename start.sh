cd CampNect_Backend
python manage.py migrate --noinput
python manage.py collectstatic --noinput
# Prefer daphne (serves HTTP + WebSockets for real-time chat).
# If daphne is unavailable (channels not installed), fall back to gunicorn — the
# app degrades gracefully to HTTP polling for chat.
if command -v daphne >/dev/null 2>&1; then
    daphne -b 0.0.0.0 -p $PORT CampNect_Backend.asgi:application
else
    gunicorn CampNect_Backend.wsgi --bind 0.0.0.0:$PORT
fi
