# Deployment Guide

## Deploying CampNect to Railway (Free Trial)

### Prerequisites
- A [GitHub](https://github.com) account
- A [Railway](https://railway.com) account (free trial includes $5 credit)
- Your code pushed to GitHub

### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/Asadalvi979/CampNect.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Railway

1. Go to [railway.com](https://railway.com) and sign in
2. Click **New Project** → **Deploy from GitHub repo**
3. Select your `CampNect` repository
4. Railway automatically detects Django from `requirements.txt`

### Step 3: Add MySQL Database

1. In the Railway project canvas, click **Create** → **Database** → **MySQL**
2. Set the following variables in the MySQL service:
   - `MYSQL_ROOT_PASSWORD` — choose a strong password
   - `MYSQL_DATABASE` — `campnect_db`
3. Click **Deploy** on the MySQL service
4. Add a **Volume** to the MySQL service:
   - Go to MySQL service **Settings** → **Volumes**
   - Add volume mounted at `/var/lib/mysql`
   - This ensures database data persists across redeploys

### Step 4: Configure Environment Variables

In your Django service, go to the **Variables** tab and add:

| Variable | Value | Notes |
|----------|-------|-------|
| `NIXPACKS_PATH` | `CampNect_Backend` | Tells Railway where `manage.py` lives |
| `SECRET_KEY` | *(generate new)* | Run `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | `False` | Disables debug mode |
| `ALLOWED_HOSTS` | `.up.railway.app` | Allows Railway-generated domains |
| `CSRF_TRUSTED_ORIGINS` | `https://*.up.railway.app` | CSRF protection for Railway domain |
| `DB_NAME` | `campnect_db` | MySQL database name |
| `DB_USER` | `root` | MySQL user |
| `DB_PASSWORD` | *(your MYSQL_ROOT_PASSWORD)* | MySQL root password |
| `DB_HOST` | `${{MySQL.MYSQL_HOST}}` | Railway service reference |
| `DB_PORT` | `3306` | MySQL port |
| `EMAIL_HOST` | `smtp.gmail.com` | SMTP server |
| `EMAIL_PORT` | `587` | SMTP port |
| `EMAIL_HOST_USER` | `asadalvi979@gmail.com` | Your Gmail address |
| `EMAIL_HOST_PASSWORD` | *(your Gmail app password)* | Gmail App Password |
| `SITE_URL` | *(set after getting domain)* | Will update later |

### Step 5: Deploy

1. Click **Deploy** on your Django service
2. Wait for the build to complete (check **View Logs**)
3. Go to **Settings** → **Networking** → **Generate Domain**
4. Copy the generated URL (e.g., `campnect-production.up.railway.app`)
5. Update `SITE_URL` to `https://your-domain.up.railway.app`

### Step 6: Run Migrations

1. Open the **Shell** tab in your Django service
2. Run:
```bash
python manage.py migrate
python manage.py createsuperuser
```

### Step 7: Verify

Visit your Railway domain. You should see the CampNect landing page.

---

## Production Checklist

- [ ] Generate a strong `SECRET_KEY`
- [ ] Set `DEBUG=False`
- [ ] Configure custom domain (optional)
- [ ] Set up automated database backups
- [ ] Configure media file storage (Backblaze B2 / AWS S3)
- [ ] Enable monitoring (Sentry, etc.)

---

## Media Files in Production

Railway uses ephemeral storage — uploaded files are lost on each deploy. For production:

### Option 1: Backblaze B2 (Free tier: 10GB)
1. Create a Backblaze account
2. Create a B2 bucket
3. Install `django-storages` and `boto3`
4. Configure `DEFAULT_FILE_STORAGE` in settings.py

### Option 2: AWS S3
1. Create an S3 bucket
2. Configure IAM user with programmatic access
3. Use `django-storages` with S3 backend

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: MySQLdb` | Ensure `mysqlclient` is in `requirements.txt` |
| Build fails | Check build logs — verify `NIXPACKS_PATH` is set correctly |
| `DisallowedHost` error | Add your domain to `ALLOWED_HOSTS` |
| Email not sending | Verify Gmail App Password (not regular password) |
| Static files 404 | Run `python manage.py collectstatic` and check WhiteNoise is in MIDDLEWARE |
