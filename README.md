<div align="center">
  <h1>🏕️ CampNect</h1>
  <p><strong>University Campus Connect Platform</strong></p>
  <p>Bridging students, seniors, and alumni through meaningful collaboration</p>

  <p>
    <a href="https://www.python.org/downloads/release/python-3135/">
      <img src="https://img.shields.io/badge/python-3.13.5-blue?logo=python&logoColor=white" alt="Python 3.13.5">
    </a>
    <a href="https://www.djangoproject.com/">
      <img src="https://img.shields.io/badge/django-6.0-092E20?logo=django&logoColor=white" alt="Django 6.0">
    </a>
    <a href="https://www.mysql.com/">
      <img src="https://img.shields.io/badge/database-mysql-4479A1?logo=mysql&logoColor=white" alt="MySQL">
    </a>
    <a href="https://github.com/Asadalvi979/CampNect/blob/main/LICENSE">
      <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
    </a>
    <a href="https://railway.com">
      <img src="https://img.shields.io/badge/deploy-ready-7B2FF7?logo=railway&logoColor=white" alt="Deploy Ready">
    </a>
  </p>

  <br>
  <img src="https://img.shields.io/github/stars/Asadalvi979/CampNect?style=social" alt="GitHub stars">
  <img src="https://img.shields.io/github/forks/Asadalvi979/CampNect?style=social" alt="GitHub forks">
</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Architecture](#-architecture)
- [Getting Started](#-getting-started)
- [Deployment](#-deployment)
- [API Reference](#-api-reference)
- [Project Structure](#-project-structure)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

**CampNect** is a comprehensive web platform designed to connect university students, seniors, and alumni within a single ecosystem. It enables academic collaboration, mentorship opportunities, community building, and professional networking — all tailored to the university experience.

Built for **Riphah International University** but adaptable to any institution.

### Why CampNect?

- 🎓 **Role-based access** — Students, Seniors (Semester 5+), Alumni, and Admins each have tailored experiences
- 🔐 **University CMS authentication** — Secure login using institutional IDs with email OTP verification
- 🤝 **Structured mentorship** — Alumni mentor current students with a formal request/accept workflow
- 📚 **Resource sharing** — Upload and discover study notes, project resources, and academic materials

---

## ✨ Features

### 🔐 Authentication & Security
| Feature | Details |
|---------|---------|
| CMS-based login | University ID as the primary identifier (no usernames) |
| Email OTP verification | 5-minute OTP with resend capability |
| Password reset | Forgot/reset flow with email verification |
| Rate limiting | Login (10/min), registration (5/min), password reset (10/min) |

### 👥 Community
- Create and join **subject-based communities** (CS, SE, AI, General)
- Community **discussion boards** with threaded replies
- Role management: members, moderators, founders
- Configurable posting permissions (all members / admins only)
- **Group chat** per community

### 🧭 Mentorship
- **Alumni directory** with filters (industry, company, graduation year)
- Send/receive **mentorship requests** with subject and reason
- Accept/reject workflow with status tracking
- **One-on-one mentorship chat** with file sharing
- Role-based access control (semester 1-4 restricted from direct alumni contact)

### 🤝 Collaboration
- **Project collaboration posts** with required skills and roles
- Interest/team/decline system
- Per-project **collaboration chat**
- Like and comment on projects (nested replies)

### 💬 Messaging
- **Direct one-on-one messaging** with file attachments
- Real-time conversation list
- File upload support for chat, notes, and profiles

### 📄 Notes & Resources
- Upload study notes (PDF, DOC, PPT, images)
- Filter by **subject, semester, and community**
- Paginated browsing (20 per page)

### 📢 Announcements
- Pinned and chronological announcements
- **Like** and **comment** system (nested replies)
- Admin posting with customizable byline

### 🔔 Notifications
- Real-time notification feed
- Types: mentorship requests, messages, connections, community joins
- Unread count badge
- Mark-as-read functionality

### 👤 User Profiles
- Custom role-based profiles: students, seniors, alumni
- Profile pictures, bio, skills display
- Alumni-specific: company, position, industry, graduation year
- **Follow/unfollow** system (Connection model)
- Quick-view popup on hover

### 📊 Admin Panel
- Comprehensive analytics dashboard
- CRUD management for users, communities, announcements, notes, projects
- Activity monitoring

---

## 🛠 Tech Stack

### Backend
| Technology | Purpose |
|------------|---------|
| [Django 6.0](https://www.djangoproject.com/) | Web framework |
| [MySQL](https://www.mysql.com/) | Database (`utf8mb4` encoding) |
| [Gunicorn](https://gunicorn.org/) | Production WSGI server |
| [WhiteNoise](https://whitenoise.readthedocs.io/) | Static file serving |
| [django-ratelimit](https://django-ratelimit.readthedocs.io/) | Rate limiting & brute-force protection |
| [Pillow](https://python-pillow.org/) | Image processing |
| [python-dotenv](https://github.com/theskumar/python-dotenv/) | Environment variable management |

### Frontend
| Technology | Purpose |
|------------|---------|
| HTML5 + Django Templates | Server-rendered pages |
| CSS3 (custom) | Responsive design with theme support |
| Vanilla JavaScript | Interactive UI (14 modules, ~140KB) |
| Font Awesome 6 | Icon library |

---

## 🏗 Architecture

```
User → DNS → Reverse Proxy (Railway) → Gunicorn → Django
                                              ├── MySQL Database
                                              ├── WhiteNoise (Static Files)
                                              └── Media Storage (Local / S3)
```

### Models (24 total)

```
User (Custom) ───┬── OTP
                 ├── Community ─── CommunityMember
                 ├── Message (1:1)
                 ├── Connection (Follow system)
                 ├── Announcement ─── AnnouncementLike
                 │                   └── AnnouncementComment
                 ├── CollaborationPost ─── CollaborationPostLike
                 │                       ├── CollaborationPostComment
                 │                       └── CollaborationPostInterest
                 ├── Mentorship ─── MentorshipMessage
                 │                └── MentorshipRequest
                 ├── CommunityMessage
                 ├── CollaborationMessage
                 ├── Note
                 ├── Event
                 ├── Notification
                 └── CareerOpportunity
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.13+
- MySQL 8.0+
- pip (Python package manager)

### Installation

```bash
# Clone the repository
git clone https://github.com/Asadalvi979/CampNect.git
cd CampNect

# Set up virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\activate       # Windows

# Install dependencies
cd CampNect_Backend
pip install -r requirements.txt

# Configure environment
cp .env.production .env
# Edit .env with your database credentials and settings

# Run migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

Visit **http://127.0.0.1:8000** to see the app.

### Environment Variables

Create a `.env` file in `CampNect_Backend/`:

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=campnect_db
DB_USER=root
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=3306

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=CampNect <your-email@gmail.com>
SITE_URL=http://127.0.0.1:8000
```

---

## 🌐 Deployment

CampNect is **deploy-ready** with:

- ✅ **Procfile** — Gunicorn WSGI configuration
- ✅ **runtime.txt** — Python version pinning
- ✅ **railway.toml** — Railway deployment config
- ✅ **WhiteNoise** — Production static file serving
- ✅ **HTTPS security** — HSTS, secure cookies, SSL redirect (enabled with `DEBUG=False`)

### Deploy to Railway (Free Trial)

```bash
# 1. Push to GitHub
git push origin main

# 2. Go to railway.com → New Project → Deploy from GitHub
# 3. Add MySQL database service
# 4. Set environment variables in Railway dashboard
# 5. Deploy! 🚀
```

See [Deployment Guide](DEPLOYMENT.md) for detailed instructions.

---

## 📖 API Reference

CampNect exposes RESTful JSON endpoints for key features:

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/user/<id>/` | GET | Required | User profile data |
| `/api/alumni-list/` | GET | Required | Filtered alumni directory |
| `/api/send-mentorship-request/` | POST | Required | Send mentorship request |
| `/api/mentorship-requests/` | GET | Required | List mentorship requests |
| `/api/handle-mentorship-request/` | POST | Required | Accept/reject request |
| `/api/update-alumni-profile/` | POST | Alumni | Update professional info |
| `/api/notifications/` | GET/POST | Required | Notification feed |
| `/api/notifications/unread-count/` | GET | Required | Unread count |

---

## 📁 Project Structure

```
CampNect/
├── CampNect_Backend/           # Django project root
│   ├── CampNect_Backend/       # Project configuration
│   │   ├── settings.py         # Django settings
│   │   ├── urls.py             # Root URL config
│   │   ├── wsgi.py             # WSGI entry point
│   │   └── asgi.py             # ASGI entry point
│   ├── core/                   # Main application
│   │   ├── models.py           # 24 database models
│   │   ├── views.py            # 30+ views
│   │   ├── urls.py             # URL routing
│   │   ├── forms.py            # Model forms
│   │   ├── admin.py            # Admin interface
│   │   ├── signals.py          # Event signals
│   │   ├── permissions.py      # Access control
│   │   ├── context_processors.py
│   │   └── migrations/         # Database migrations
│   ├── manage.py
│   ├── requirements.txt
│   └── .env.production
├── frontend/
│   ├── publicPage/             # Public pages (login, register, etc.)
│   │   ├── assets/
│   │   │   ├── css/            # 14 CSS modules
│   │   │   └── js/             # 14 JavaScript modules
│   │   ├── images/
│   │   ├── index.html
│   │   └── style.css
│   └── Users/                  # Authenticated user pages
│       ├── dashboard.html
│       ├── chat.html
│       ├── profile.html
│       ├── mentorship.html
│       ├── communities.html
│       └── emails/             # Email templates
├── Procfile
├── runtime.txt
├── railway.toml
├── .gitignore
└── README.md
```

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

Please ensure your code follows the existing style and includes relevant tests.

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for more information.

---

<div align="center">
  <p>Built with ❤️ for Riphah International University</p>
  <p>
    <a href="https://github.com/Asadalvi979/CampNect/issues">Report Bug</a>
    ·
    <a href="https://github.com/Asadalvi979/CampNect/issues">Request Feature</a>
  </p>
  <br>
  <p>
    <a href="https://github.com/Asadalvi979/CampNect">
      <img src="https://img.shields.io/badge/⭐_Star_on_GitHub-CampNect-blue?style=for-the-badge" alt="Star on GitHub">
    </a>
  </p>
</div>
