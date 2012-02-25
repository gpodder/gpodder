#!/bin/sh

set -e

for translation in `dirname $0`/../../po/*.po; do
    echo "Checking: $translation"
    msgfmt --check "$translation"
done

