from setuptools import setup, find_packages


def _is_requirement(line):
    """Returns whether the line is a valid package requirement."""
    line = line.strip()
    return line and not (line.startswith("-r") or line.startswith("#"))


def _read_requirements(filename):
    """Returns a list of package requirements read from the file."""
    requirements_file = open(filename).read()
    return [line.strip() for line in requirements_file.splitlines()
            if _is_requirement(line)]


required_packages = _read_requirements("requirements/base.txt")
test_packages = _read_requirements("requirements/tests.txt")


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
    test_suite='run_tests.run_django_tests',
    tests_require=required_packages + test_packages,
    url='https://github.com/caktus/django-timepiece',
    version=__import__('timepiece').__version__,
    zip_safe=False,  # because we're including media that Django needs
)
