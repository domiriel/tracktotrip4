"""
Setup script
"""
import os
from distutils.core import setup
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

def read(filename):
    """ Reads file
    """
    with open(os.path.join(os.path.dirname(__file__), filename), 'r', encoding='utf16') as f:
        return f.read().splitlines()

VERSION = '0.1.2'



setup(
    name='tracktotrip4',
    packages=['tracktotrip4'],
    version=VERSION,
    description='Track processing library for Python 3',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Daniel Gonçalves, Daniel Serafim, Rui Gil',
    author_email='dserafim1999@gmail.com',
    url='https://github.com/domiriel/tracktotrip4',
    download_url='https://github.com/domiriel/tracktotrip4/releases/tag/%s' % VERSION,
    keywords=['track', 'trip', 'GPS', 'GPX'],
    classifiers=[],
    scripts=[
        'scripts/tracktotrip_util',
        'scripts/tracktotrip_geolife_dataset'
    ],
    install_requires=read('requirements.txt')
)
