from .base import *  # noqa


# In tests, compressor has a habit of choking on failing tests and masking
# the real error.
COMPRESS_ENABLED = False

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]
