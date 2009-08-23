#!/bin/sh

cat <<EOF

  Checking translations for formal errors...

EOF

for translation in *.po; do
    echo "     Checking: $translation"
    msgfmt --check "$translation" || exit 1
done

cat <<EOF

  Translation check finished. Strings looking good.

EOF

