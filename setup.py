from setuptools import setup, find_packages


required_packages = [
    'Django>=1.6',
    'django-appconf==0.6',
    'django-bootstrap-toolkit==2.15.0',
    'django-compressor==1.4',
    'django-selectable==0.9.0',
    'psycopg2==2.5.4',
    'python-dateutil==2.4.0',
    'pytz==2014.10',
    'six==1.9.0',
]

test_packages = [
    'factory-boy==2.4.1',
    'Mock==1.0.1',
]

setup(
    author='Caktus Consulting Group, LLC',
    author_email='solutions@caktusgroup.com',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Natual Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Office/Business :: Financial :: Accounting',
        'Topic :: Office/Business :: Scheduling',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    description="A multi-user application for tracking employee time on projects.",
    packages=find_packages(exclude=['example_project']),
    include_package_data=True,
    install_requires=required_packages,
    license='BSD',
    long_description=open('README.rst').read(),
    name='django-timepiece',
    test_suite='run_tests.run',
    tests_require=required_packages + test_packages,
    url='https://github.com/caktus/django-timepiece',
    version=__import__('timepiece').__version__,
    zip_safe=False,  # because we're including media that Django needs
)
