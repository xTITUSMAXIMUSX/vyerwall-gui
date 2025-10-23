import traceback

def build(paths):
    data = []
    for path in paths:
        if isinstance(path, list):
            data.append(path)
        else:
            raise TypeError('not list')
    # mimic configure_set
    payload = {'data': data}
    if not data:
        raise IndexError('list index out of range')
    return payload

try:
    build([])
except Exception as exc:
    print('error:', exc)
    traceback.print_exc()
