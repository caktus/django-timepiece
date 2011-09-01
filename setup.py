from setuptools import setup, find_packages

setup(
    name='django-timepiece',
    version='0.2.0',
    author='Caktus Consulting Group',
    author_email='solutions@caktusgroup.com',
    packages=find_packages(),
    include_package_data=True,
    exclude_package_data={
        '': ['*.sql', '*.pyc',],
    },
    url='',
    license='LICENSE.txt',
    description='django-timepiece',
    long_description=open('README.rst').read(),
)
