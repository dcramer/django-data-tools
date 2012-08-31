# Hack to prevent stupid "TypeError: 'NoneType' object is not callable" error
# in multiprocessing/util.py _exit_function when running `python
# setup.py test` (see
# http://www.eby-sarna.com/pipermail/peak/2010-May/003357.html)
try:
    import multiprocessing
except ImportError:
    pass

from setuptools import setup, find_packages

tests_require = [
    'Django>=1.2,<1.4',
    'django-nose',
    'nose',
]

tests_require = [
]

setup(
    name='django-data-tools',
    version='0.1.0',
    description='',
    author='David Cramer',
    author_email='dcramer@gmail.com',
    url='https://github.com/dcramer/django-data-tools',
    tests_require=tests_require,
    test_suite='runtests.runtests',
    license='Apache License 2.0',
    packages=find_packages(),
    zip_safe=False,
    # test_suite='runtests.runtests',
    include_package_data=True,
)
