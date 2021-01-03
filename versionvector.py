"""
A version vector is a dict from replica IDs (strings) to counters (ints).
"""


def check(vv):
    """
    Raises ValueError if vv is not a version vector.

    Fails if not dict:
    >>> check('hi')
    Traceback (most recent call last):
    ValueError: version vector is not dict
    >>> check(None)
    Traceback (most recent call last):
    ValueError: version vector is not dict
    >>> check({'a', 'b'})
    Traceback (most recent call last):
    ValueError: version vector is not dict

    Accepts the empty dict:
    >>> check({})

    Fails if a key is not str:
    >>> check({'a': 1, 2: 2})
    Traceback (most recent call last):
    ValueError: version vector key is not str
    >>> check({'a': 1, None: 1})
    Traceback (most recent call last):
    ValueError: version vector key is not str

    Fails if a value is not int:
    >>> check({'a': 3, 'b': '4'})
    Traceback (most recent call last):
    ValueError: version vector value is not int
    >>> check({'R': 0, 'S': None})
    Traceback (most recent call last):
    ValueError: version vector value is not int
    >>> check({'i': 0, 'f': 2.0})
    Traceback (most recent call last):
    ValueError: version vector value is not int

    Accepts a dict from str to int:
    >>> check({'X': 1})
    >>> check({'A': 0, 'B': 5})
    """
    if type(vv) is not dict:
        raise ValueError('version vector is not dict')
    if any(type(k) is not str for k in vv):
        raise ValueError('version vector key is not str')
    if any(type(v) is not int for v in vv.values()):
        raise ValueError('version vector value is not int')


def leq(x, y):
    """
    Returns x ⊑ y (True or False).

    x ⊑ y ⇔ every x key exists in y and its x counter ≤ its y counter.

    >>> leq({}, {'A':1})
    True
    >>> leq({'A':1} , {'A':1})
    True
    >>> leq({'A':1}, {'A':2, 'B':3})
    True
    >>> leq({'A':1, 'B':2}, {'B':3})
    False
    >>> leq({'A':1, 'B':2}, {'A':3, 'B':1})
    False
    >>> leq({'A':1, 'B':2}, {'A':1, 'B':3})
    True

    ∀ x: leq(x, x)
    >>> all(leq(x, x) for x in ({}, {'A': 1, 'Z': 26}))
    True
    """
    for vv in (x, y):
        check(vv)
    del vv

    return all(k in y and x[k] <= y[k] for k in x)


def join(x, y):
    """
    Returns x ⊔ y.

    x ⊔ y has the union of x and y's replica IDs.
    A replica ID's counter is the maximum of its counters in x and y
    if it is present in both, else its counter from x or y where it is present.

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
    return result


def advance(key, vv):
    """
    Return a new dict with key's value incremented if present else set to 1.

    Fails if key is not str:
    >>> advance(3, {})
    Traceback (most recent call last):
    ValueError: key to advance is not str

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
    >>> original = {'A': 2, 'Z': 1}
    >>> copy = dict(original)
    >>> sorted(advance('Z', original).items())
    [('A', 2), ('Z', 2)]
    >>> copy == original
    True
    """
    if type(key) is not str:
        raise ValueError('key to advance is not str')
    check(vv)

    copy = dict(vv)
    copy[key] = copy.get(key, 0) + 1
    return copy
