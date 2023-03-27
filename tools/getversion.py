import os
import re
from pathlib import Path

here = Path(__file__).parent or '.'
main_module = open(os.path.join(here, '../src/gpodder/__init__.py')).read()
metadata = dict(re.findall("__([a-z_]+)__\s*=\s*'([^']+)'", main_module))
print(metadata['version'])
