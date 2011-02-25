#!/bin/sh
(for file in `find src -name '*.py'`; do echo $file; git log $file | grep -o '^Author.*' | sort -u | sed -e 's/^/  /g'; done) | tee authors-historic.txt
(for file in `find src -name '*.py'`; do echo $file; git blame -p $file | grep '^author ' |sort -u | sed -e 's/^/  /g'; done) | tee authors-now.txt
