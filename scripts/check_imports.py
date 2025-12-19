import sys
sys.path.insert(0, '.')

try:
    from core.genetics import genome, genome_codec, trait
    print('IMPORT_OK')
except Exception as e:
    print('IMPORT_FAILED', e)
    raise
