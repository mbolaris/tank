import sys

sys.path.insert(0, '.')

try:
    print('IMPORT_OK')
except Exception as e:
    print('IMPORT_FAILED', e)
    raise
