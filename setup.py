from setuptools import setup, find_packages


required_packages = [
    'django>=1.4',
    'psycopg2==2.5',
    'python-dateutil==1.5',
    'django-pagination==1.0.7',
    'django-selectable==0.4.1',
    'django-bootstrap-toolkit==2.5.6',
    'django-compressor==1.2',
    'pytz==2012c',
]

test_packages = [
    'Mock==1.0.1',
    'factory-boy==2.1.1',
    'coverage==3.5.3',
]

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
    tests_require=required_packages + test_packages,
    test_suite='run_tests.run',
    install_requires=required_packages,
)
