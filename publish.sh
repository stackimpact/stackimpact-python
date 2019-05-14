#!/bin/bash

set -e

pandoc --from=markdown --to=rst --output=README.rst 'README.md'

python3 -m unittest discover -v -s tests -p *_test.py

rm -f dist/*.tar.gz
python setup.py sdist

for bundle in dist/*.tar.gz; do
	echo "Publishing $bundle..."
	twine upload $bundle
done
