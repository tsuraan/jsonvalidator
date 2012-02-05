import sys
import os

from distutils.core import setup

version = '0.0.1'

setup(
    name='jsonvalidator',
    version=version,
    description='A JSON "Schema By Example" validation.',
    long_description='''
    ''',
    url='https://github.com/tsuraan/jsonvalidator',
    packages=['jsonvalidator',
              ],
    author='Max Derkachev',
    download_url='http://github.com/tsuraan/jsonvalidator/tarball/jsonvalidator-%s' % (version,),
    classifiers=[
    "Development Status :: 4 - Beta",
    "Environment :: Web Environment",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: BSD License",
    "Operating System :: POSIX",
    "Programming Language :: Python",
    "Topic :: Internet :: WWW/HTTP",
    "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    )
