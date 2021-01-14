def check(vv):
    """
    Raise an exception if vv is not a version vector.

    >>> check({'a'})
    Traceback (most recent call last):
    ValueError: version vector is not dict
    >>> check({3: 3, 'a': 1})
    Traceback (most recent call last):
    ValueError: version vector key is not str
    >>> check({'a': '1', 'b': 2})
    Traceback (most recent call last):
    ValueError: version vector value is not int

    >>> check({})
    >>> check({'a': 1, 'other': 17})
    """
    if type(vv) is not dict:
        raise ValueError('version vector is not dict')
    if any(type(k) is not str for k in vv):
        raise ValueError('version vector key is not str')
    if any(type(val) is not int for val in vv.values()):
        raise ValueError('version vector value is not int')


def less(a, b):
    """
    >>> all(less(a, b) for (a, b) in (
    ...     ({}, {'A': 1}),
    ...     ({'A': 1}, {'A': 2, 'B': 3}),
    ...     ({'A': 1, 'B': 2}, {'A': 1, 'B': 3}),
    ... ))
    True

    >>> any(less(a, b) for (a, b) in (
    ...     ({'A': 1}, {'A': 1}),
    ...     ({'A': 1, 'B': 2}, {'B': 3}),
    ...     ({'A': 1, 'B': 2}, {'A': 3, 'B': 1}),
    ... ))
    False
    """
    for vv in (a, b):
        check(vv)
    del vv

    return a != b and all(k in b and a[k] <= b[k] for k in a)


def join(a, b):
    """
    >>> sorted(join({'A': 1}, {'A': 2}).items())
    [('A', 2)]
    >>> sorted(join({'A': 1}, {'B': 2}).items())
    [('A', 1), ('B', 2)]
    >>> sorted(join({'A': 1, 'B': 4, 'C': 2, 'D': 6},
    ...                     {'B': 3, 'C': 2, 'D': 7, 'E': 9}).items())
    [('A', 1), ('B', 4), ('C', 2), ('D', 7), ('E', 9)]

    >>> in_a, in_b = {'A': 1}, {'B': 1}
    >>> out_j = join(in_a, in_b)
    >>> out_j is in_a
    False
    >>> out_j is in_b
    False
    >>> del in_a, in_b, out_j
    """
    for vv in (a, b):
        check(vv)
    del vv

    result = dict(a)
    for k in b:
        if k not in result or result[k] < b[k]:
            result[k] = b[k]

    check(result)
    return result


def advance(key, vv):
    """
    Return a new version vector with key's counter incremented or 1 if absent.

    >>> sorted(advance('q', {}).items())
    [('q', 1)]
    >>> sorted(advance('y', {'x': 2, 'y': 17}).items())
    [('x', 2), ('y', 18)]

    >>> in_v = {'x': 4}
    >>> advance('y', in_v) is in_v
    False
    >>> del in_v
    """
    check(vv)
    result = dict(vv)
    result[key] = result.get(key, 0) + 1
    check(result)
    return result
