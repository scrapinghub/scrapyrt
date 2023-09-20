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
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Operating System :: OS Independent',
        'Environment :: Console',
        'Environment :: No Input/Output (Daemon)',
        'Topic :: Internet :: WWW/HTTP',
        'License :: OSI Approved :: BSD License',
    ],
    project_urls={
        "Documentation": "https://scrapyrt.readthedocs.io/en/latest/index.html",
        "Source": "https://github.com/scrapinghub/scrapyrt",
        "Tracker": "https://github.com/scrapinghub/scrapyrt/issues"
    },
    install_requires=[
        'Scrapy>=2.10'
    ],
    package_data={
        'scrapyrt': [
            'VERSION',
        ]
    },
    python_requires='>=3.8',
)
