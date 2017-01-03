import sys
from setuptools import setup, find_packages


with open('requirements.txt') as f:
    deps = [dep for dep in f.read().split('\n') if dep.strip() != '']
    install_requires = deps


setup(name='restjson',
      version="0.1",
      packages=find_packages(),
      description="Client library for RESTful JSON services",
      include_package_data=True,
      zip_safe=False,
      install_requires=install_requires)
