from setuptools import setup, find_packages


required_packages = open("example_project/requirements/base.txt").read()
required_packages = [r.strip() for r in required_packages.splitlines() if r.strip()]

test_packages = open("example_project/requirements/tests.txt").read()
test_packages = [t.strip() for t in test_packages.splitlines()
                 if t.strip() and not t.strip().startswith("-r")]

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
