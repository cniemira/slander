import os
import sys

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()

requires = [
    'slackclient',
    'terminaltables',
    ]

setup(name='slander',
      author='CJ Niemira',
      author_email='siege@siege.org',
      version='0.1',
      description='SLack Agile Not Dangerously Evil Robot',
      long_description=README,
      classifiers=[
          "Programming Language :: Python",
      ],
      url='https://github.com/siege/slander',
      keywords='agile chat slack standup',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite=None,
      install_requires=requires,
      entry_points="""\
      [console_scripts]
      slanderbot = slander:main
      """,
      )
