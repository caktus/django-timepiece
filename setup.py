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
    zip_safe=False, # because we're including media that Django needs
    description="django-timepiece is a multi-user application for tracking "
                "people's time on projects.",
    classifiers=[
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Development Status :: 4 - Beta',
        'Operating System :: OS Independent',
    ],
    install_requires = [
        "python-dateutil==1.5",
        "django-ajax-selects==1.1.4",
        "django-pagination==1.0.7",
        "django-selectable==0.2.0",
    ],
)
