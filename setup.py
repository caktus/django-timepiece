from setuptools import setup, find_packages

setup(
    name='django-timepiece',
    version=__import__('timepiece').__version__,
    author='Caktus Consulting Group',
    author_email='solutions@caktusgroup.com',
    packages=find_packages(exclude=['example_project']),
    include_package_data=True,
    url='https://github.com/caktus/django-timepiece',
    license='BSD',
    long_description=open('README.rst').read(),
    zip_safe=False,  # because we're including media that Django needs
    description="django-timepiece is a multi-user application for tracking "
                "people's time on projects.",
    classifiers=[
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Development Status :: 4 - Beta',
        'Operating System :: OS Independent',
    ],
    tests_require=[
        'django==1.4',
        'python-dateutil==1.5',
        'django-pagination==1.0.7',
        'django-selectable==0.4.1',
        'django-bootstrap-toolkit==2.5.6',
        'django-compressor==1.1.2',
        'pytz==2012c'
    ],
    test_suite='run_tests.run',
    install_requires=[
        'psycopg2==2.4.1',
        'python-dateutil==1.5',
        'django-pagination==1.0.7',
        'django-selectable==0.4.1',
        'django-bootstrap-toolkit==2.5.6',
        'django-compressor==1.1.2',
        'pytz==2012c'
    ],
)
