from settings.base import *


DEBUG = False
ALLOWED_HOSTS = ["yourdomain.com"]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
    }
}