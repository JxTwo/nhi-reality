import os
from pathlib import Path
import environ
from django.core.exceptions import ImproperlyConfigured
from celery.schedules import crontab

# Initialize environment
env = environ.Env(
    DEBUG=(bool, False),
)

ALLOWED_HOSTS = [
    "nhi-reality.fly.dev",
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
]

# Set BASE_DIR
BASE_DIR = Path(__file__).resolve().parent.parent

# Load correct .env file based on DJANGO_ENV
DJANGO_ENV = os.getenv("DJANGO_ENV", "development")
env_file = BASE_DIR / f".env.{DJANGO_ENV}"
environ.Env.read_env(env_file)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY", default="unsafe-default-key")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG")

DEFAULT_FLY_DOMAINS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "nhi-reality.fly.dev",
]

CSRF_TRUSTED_ORIGINS = [
    "https://nhi-reality.fly.dev",
    # add "https://yourdomain.com" when you point one
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_celery_beat',
    'disclosure',
    'evidence',
    'history',
    'news.apps.NewsConfig',
    'secrecy',
    'consciousness',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                "news.context_processors.ingestion_status",
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


ON_FLY = bool(os.getenv("FLY_APP_NAME"))

try:
    if ON_FLY:
        # On Fly we require a real DB; fail fast if missing
        DATABASES = {'default': env.db('DATABASE_URL')}
    else:
        # Local/CI can fall back to SQLite if DATABASE_URL is absent
        DATABASES = {'default': env.db('DATABASE_URL')}
except ImproperlyConfigured:
    if ON_FLY:
        # Make it obvious in deploy logs if DATABASE_URL isn't set
        raise
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'build.db',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# --- Static files -----------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# Default auto field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Celery configuration
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

# You currently run Django in UTC. Keep Celery aligned.
CELERY_TIMEZONE = TIME_ZONE  # "UTC"
CELERY_ENABLE_UTC = True

# Robustness: avoid stuck connections and allow worker to survive redis hiccups
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "visibility_timeout": 60 * 60,  # 1h; task returns to queue if worker dies mid-run
    "socket_timeout": 10,
    "socket_connect_timeout": 10,
    "retry_on_timeout": True,
}

# Code-driven schedule: every 4 hours (at :00)
CELERY_BEAT_SCHEDULE = {
    "news-fetch-all-every-4-hours": {
        "task": "news.tasks.fetch_all_news",
        "schedule": crontab(minute=0, hour="*/4"),
    }
}

REDIS_CACHE_URL = os.getenv("REDIS_CACHE_URL", REDIS_URL)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_CACHE_URL,
        "TIMEOUT": 300,
        "OPTIONS": {
            "KEY_PREFIX": "cache",
        },
    }
}