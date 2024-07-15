from setuptools import setup

setup(
    name='Nevermore',
    version='0.1',
    py_modules=['Nevermore'],
    install_requires=[
        'Click',
        'google-cloud-storage',
        'google-cloud-aiplatform',
        'asyncio',
        'protobuf>=3.19.5,<5.0.0dev'
    ],
    entry_points='''
        [console_scripts]
        nevermore=Nevermore:write_lesson_command
    ''',
)
