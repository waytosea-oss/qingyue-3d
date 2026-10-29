import sys
print('PY', sys.executable, sys.version)
for m in ('numpy', 'scipy', 'skimage', 'PIL', 'mcubes'):
    try:
        mod = __import__(m)
        print('HAVE', m, getattr(mod, '__version__', ''))
    except Exception as e:
        print('NO', m)
