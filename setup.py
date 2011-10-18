from setuptools import setup, find_packages

setup(
    name='django-data-tools',
    version='0.1',
    description='',
    author='David Cramer',
    author_email='dcramer@gmail.com',
    url='https://github.com/dcramer/django-data-tools',
    packages=find_packages(),
    zip_safe=False,
    # test_suite='runtests.runtests',
    include_package_data=True,
)
