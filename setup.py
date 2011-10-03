from setuptools import setup, find_packages

setup(
    name='django-timepiece',
    version=__import__('timepiece').__version__,
    author='Caktus Consulting Group',
    author_email='solutions@caktusgroup.com',
    packages=find_packages(),
    include_package_data=True,
    exclude_package_data={
        '': ['*.sql', '*.pyc',],
    },
    url='',
    license='BSD',
    description='django-timepiece',
    long_description=open('README.rst').read(),
    zip_safe=False, # because we're including media that Django needs
)
