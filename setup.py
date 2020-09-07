from setuptools import setup


setup(
    name='sqlfs',
    version='1.0.0',
    py_modules=['sqlfs'],
    scripts=['sqlfs'],
    install_requires=[
        'pyfuse3',
    ]
)
