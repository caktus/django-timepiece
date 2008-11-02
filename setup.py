#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup
import sys, os

def fullsplit(path, result=None):
    """
    Split a pathname into components (the opposite of os.path.join) in a
    platform-neutral way.
    """
    if result is None:
        result = []
    head, tail = os.path.split(path)
    if head == '':
        return [tail] + result
    if head == path:
        return result
    return fullsplit(head, [tail] + result)

packages, data_files = [], []
root_dir = os.path.dirname(__file__)
if root_dir != '':
    os.chdir(root_dir)
pendulum_dir = 'pendulum'

for path, dirs, files in os.walk(pendulum_dir):
    # ignore hidden directories and files
    for i, d in enumerate(dirs):
        if d.startswith('.'): del dirs[i]

    if '__init__.py' in files:
        packages.append('.'.join(fullsplit(path)))
    elif files:
        data_files.append((path, [os.path.join(path, f) for f in files]))

setup(
    name='django-pendulum',
    version='0.1',
    url='http://code.google.com/p/django-pendulum/',
    author='Josh VanderLinden',
    author_email='codekoala@gmail.com',
    license='MIT',
    packages=packages,
    data_files=data_files,
    description="A simple timeclock/timecard application for use in Django-powered Web sites.",
    long_description="""
django-pendulum is a basic timeclock/timecard/time logging application that
can easily be plugged into a Django-powered Web site.

Features include:
    - Configuration: Pendulum can be configured to operate on several Django-
        powered sites.  The period lengths can be configured as monthly or as
        a fixed-length period.
    - Projects: You can have an unlimited number of projects to be able to
        categorize hours spent working on certain tasks.  Each project can be
        activated/deactivated as necessary via the Django admin.
    - Activities: Activities allow you to further categorize work done on
        particular tasks for each project.
"""
)