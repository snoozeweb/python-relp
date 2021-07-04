'''Setup script for pip package'''

from setuptools import setup, find_packages

setup(
    name='relp',
    version='0.0.1',
    author='Guillaume Ludinard',
    author_email='guillaume.ludi@gmail.com',
    description='Pure python implementation of RELP protocol',
    url='https://github.com/rudexi/python-relp',
    packages=find_packages(),
)
