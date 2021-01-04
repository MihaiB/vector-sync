"""
A version vector is a dict from replica IDs (strings) to counters (ints).
"""


def check(vv):
    """
    Raises ValueError if vv is not a version vector.

    Fails if not dict:
    >>> check({'a', 'b'})
    Traceback (most recent call last):
    ValueError: version vector is not dict

    Accepts the empty dict:
    >>> check({})

    Fails if a key is not str:
    >>> check({'a': 1, 2: 2})
    Traceback (most recent call last):
    ValueError: version vector key is not str

    Fails if a value is not int:
    >>> check({'a': 3, 'b': '4'})
    Traceback (most recent call last):
    ValueError: version vector value is not int
    >>> check({'i': 0, 'f': 2.0})
    Traceback (most recent call last):
    ValueError: version vector value is not int

    Accepts a dict from str to int:
    >>> check({'A': 0, 'B': 5})
    """
    if type(vv) is not dict:
        raise ValueError('version vector is not dict')
    if any(type(k) is not str for k in vv):
        raise ValueError('version vector key is not str')
    if any(type(v) is not int for v in vv.values()):
        raise ValueError('version vector value is not int')


def less(x, y):
    """
    Returns x < y (True or False).

    x < y ⇔ x ≠ y and y has equal or higher counters for all replica IDs in x.

    >>> less({}, {'A':1})
    True
    >>> less({'A':1} , {'A':1})
    False
    >>> less({'A':1}, {'A':2, 'B':3})
    True
    >>> less({'A':1, 'B':2}, {'B':3})
    False
    >>> less({'A':1, 'B':2}, {'A':3, 'B':1})
    False
    >>> less({'A':1, 'B':2}, {'A':1, 'B':3})
    True
    """
    for vv in (x, y):
        check(vv)
    del vv

    return x != y and all(k in y and x[k] <= y[k] for k in x)


def join(x, y):
    """
    Returns x ⊔ y.

    x ⊔ y has all replica IDs, each with its maximum counter.

    >>> join({'A':1}, {'A':2})
    {'A': 2}
    >>> sorted(join({'A':1}, {'B':2}).items())
    [('A', 1), ('B', 2)]
    >>> sorted(join({'A':1, 'B':4, 'C':2, 'D':6},
    ...     {'B':3, 'C':2, 'D':7, 'E':9}).items())
    [('A', 1), ('B', 4), ('C', 2), ('D', 7), ('E', 9)]

    ∀ x: join(x, x) = x
    >>> all(join(x, x) == x for x in [{}, {'A': 1, 'Z': 26}])
    True

    ∀ x: join(x, x) is not the same Python object as x
    >>> all(join(x, x) is not x for x in [{}, {'a': 27, 'z': 52}])
    True
    """
    for vv in (x, y):
        check(vv)
    del vv

    result = dict(x)
    for k in y:
        if k not in result or result[k] < y[k]:
            result[k] = y[k]
    check(result)
    return result


def advance(key, vv):
    """
    Return a new dict with key's value incremented if present else set to 1.

    >>> advance('A', {})
    {'A': 1}
    >>> sorted(advance('K', {'A': 4, 'Z': 7}).items())
    [('A', 4), ('K', 1), ('Z', 7)]
    >>> sorted(advance('B', {'A': 3, 'B': 6, 'C': 12}).items())
    [('A', 3), ('B', 7), ('C', 12)]

    It returns a different dict:
    >>> all(advance('B', v) is not v for v in ({}, {'B': 5}))
    True

    The argument is not modified:
    >>> original = {'A': 2, 'Z': 7}
    >>> advance('Z', original) == {'A': 2, 'Z': 8}
    True
    >>> original == {'A': 2, 'Z': 7}
    True
    """
    check(vv)

    result = dict(vv)
    result[key] = result.get(key, 0) + 1
    check(result)
    return result
