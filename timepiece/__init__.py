"""
django-timepiece is a multi-user application for tracking users' time on
projects.
"""

__version_info__ = {
    'major': 1,
    'minor': 1,
    'micro': 0,
    'release_level': 'final',
}


def _get_version():
    if __version_info__['release_level'] != 'final':
        version = "{major}.{minor}.{micro}-{release_level}"
    else:
        version = "{major}.{minor}.{micro}"
    return version.format(**__version_info__)


__version__ = _get_version()
