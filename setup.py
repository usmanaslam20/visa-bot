#!/usr/bin/env python3

import os

from setuptools import setup

import netherappbot

readme_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'README.rst')
with open(readme_path, encoding='utf-8') as f:
    README = f.read()

setup(
    name='netherappbot',
    version=netherappbot.VERSION,
    description=(
        'Telegram bots which watches for Netherlands embassy appointments.'),
    long_description=README,
    author='Aleksandr Derbenev',
    author_email='ya.alex-ac@yandex.com',
    url='https://github.com/alex-ac/netherappbot',
    packages=[
        'netherappbot',
    ],
    entry_points={
        'console_scripts': [
            'netherappbot = netherappbot.bot:run',
        ],
    },
    license='BSD-4-Clause',
    keywords=[
    ],
    install_requires=[
        'SQLAlchemy==1.3.8',
        'beautifulsoup4==4.8.0',
        'inflect==2.1.0',
        'python-telegram-bot==12.0.0',
        'requests==2.22.0',
        'sentry-sdk==1.14.0',
    ],
    setup_requires=[
        'pytest-runner==5.1',
    ],
    tests_require=[
        'pytest==5.1.2',
        'pytest-flake8==1.0.4',
    ],
)
