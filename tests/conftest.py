import sys
from unittest.mock import MagicMock

# pymongo and bson fail to import on this machine due to an OpenSSL conflict.
# Stub them out before any project module loads them.
for _mod in ["pymongo", "bson", "bson.codec_options"]:
    sys.modules.setdefault(_mod, MagicMock())
