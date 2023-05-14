from setuptools import setup
from mporg import VERSION

setup(
    name='MP3ORG',
    version=VERSION,
    packages=['mporg'],
    url='',
    license='GPL',
    author='Drag',
    author_email='juserysthee@gmail.com',
    description='Python tool to organize music files based on metadata',
    install_requires=[
        # List any external dependencies here, e.g. 'numpy'
            'diskcache~=5.6.1'
            'ftfy~=6.1.1'
            'musicbrainzngs~=0.7.1',
            'mutagen~=1.46.0',
            'pyacoustid~=1.2.2',
            'spotipy~=2.23.0',
            'pyacrcloud~=1.0.1',
        ],
    entry_points={
        'console_scripts': [
            'mporg=mporg.main:main'
        ]
    }
)
