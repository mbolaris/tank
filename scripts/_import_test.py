import importlib
try:
    importlib.import_module('core.simulators.base_simulator')
    print('import ok')
except Exception as e:
    import traceback
    traceback.print_exc()
    print('import failed', type(e).__name__, e)
