from setuptools import setup

setup(
    name='shop_rest',
    version='14.0.0',
    author='SINTEF Energy Research',
    description='REST server for SHOP',
    packages=[
        'shop_rest',
    ],
    package_dir={
        'shop_rest': '.',
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
      'python-multipart'
    ]
)
