
from setuptools import setup
from setuptools.command.install import install
from setuptools.command.sdist import sdist

__version__ = 'unknown'

with open('restshop/__init__.py', 'r') as f:
  line = f.readline()
  __version__ = line.split(' = ')[1][1:-1]

setup(
    name='restshop',
    version=__version__,
    author='SINTEF Energy Research',
    description='REST server for SHOP',
    packages=[
        'restshop',
    ],
    package_dir={
        'restshop': 'restshop',
    },
    url='http://www.sintef.no/programvare/SHOP',
    author_email='support.energy@sintef.no',
    license='OPEN',
    install_requires=[
      'pandas',
      'numpy',
      'fastapi',
      'uvicorn',
      'python-jose',
      'passlib',
      'python-multipart',
      'pytest',
      'pytest-order',
      'requests'
    ]
)
