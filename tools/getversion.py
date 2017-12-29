import os
import re

here = os.path.dirname(__file__) or '.'
main_module = open(os.path.join(here, '../src/gpodder/__init__.py')).read()
metadata = dict(re.findall("__([a-z_]+)__\s*=\s*'([^']+)'", main_module))
print(metadata['version'])
