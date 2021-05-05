
from setuptools import setup
from setuptools.command.install import install
from setuptools.command.sdist import sdist

from restshop.__init__ import __version__

class InstallWrapper(install):

  def run(self):

    print("installing using install wrapper")

    install.run(self)

class SdistWrapper(sdist):
  
  def run(self):

    print("installing using install wrapper")

    copy_dependencies()
    sdist.run(self)


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
    ],
      cmdclass={
      'install': InstallWrapper,
      'sdist': SdistWrapper
    }
)
