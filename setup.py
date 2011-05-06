import os
from setuptools import setup, find_packages

def read(fname):
    try:
        return open(os.path.join(os.path.dirname(__file__), fname)).read()
    except IOError:
        return ''

setup(
    name="django-remoteforeignkey",
    version="0.1",
    description='A reversed ForeignKey model field for Django.',
    long_description=read('README.rst'),
    keywords='django foreignkey reverse',
    packages=find_packages(),
    author='Charlie DeTar',
    author_email='cfd@media.mit.edu',
    url="http://github.com/yourcelf/django-remoteforeignkey",
    include_package_data=True,
)
