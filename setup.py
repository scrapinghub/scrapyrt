# -*- coding: utf-8 -*-
#!/usr/bin/python
from setuptools import setup, find_packages
from os.path import join, dirname

with open(join(dirname(__file__), 'scrapyrt/VERSION'), 'rb') as f:
    version = f.read().decode('ascii').strip()

setup(
    name="scrapyrt",
    version=version,
    author='Scrapinghub',
    author_email='info@scrapinghub.com',
    url="https://github.com/scrapinghub/scrapyrt",
    maintainer='Scrapinghub',
    maintainer_email='info@scrapinghub.com',
    description='Put Scrapy spiders behind an HTTP API',
    long_description=open('README.rst').read(),
    license='BSD',
    packages=find_packages(),
    entry_points={
        'console_scripts': ['scrapyrt = scrapyrt.cmdline:execute']
    },
    zip_safe=False,
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Operating System :: OS Independent',
        'Environment :: Console',
        'Environment :: No Input/Output (Daemon)',
        'Topic :: Internet :: WWW/HTTP',
        'License :: OSI Approved :: BSD License',
    ],
    install_requires=[
        'Twisted>=14.0.0',
        'Scrapy>=1.0.0',
        'demjson'
    ],
    package_data={
        'scrapyrt': [
            'VERSION',
        ]
    },
)
