"""
A version vector is a dict from replica IDs (strings) to counters (ints).
"""


def check(vv):
    """
    Raises ValueError if vv is not a version vector.

    Fails if not dict:
    >>> check('hi')
    Traceback (most recent call last):
    ValueError: not a dict
    >>> check(None)
    Traceback (most recent call last):
    ValueError: not a dict
    >>> check({'a', 'b'})
    Traceback (most recent call last):
    ValueError: not a dict

    Accepts the empty dict:
    >>> check({})

    Fails is a key is not str:
    >>> check({'a': 1, 2: 2})
    Traceback (most recent call last):
    ValueError: key is not str
    >>> check({'a': 1, None: 1})
    Traceback (most recent call last):
    ValueError: key is not str

    Fails if a value is not int:
    >>> check({'a': 3, 'b': '4'})
    Traceback (most recent call last):
    ValueError: value is not int
    >>> check({'R': 0, 'S': None})
    Traceback (most recent call last):
    ValueError: value is not int
    >>> check({'i': 0, 'f': 2.0})
    Traceback (most recent call last):
    ValueError: value is not int

    Accepts a dict from str to int:
    >>> check({'X': 1})
    >>> check({'A': 0, 'B': 5})
    """
    if type(vv) is not dict:
        raise ValueError('not a dict')
    if any(type(k) is not str for k in vv):
        raise ValueError('key is not str')
    if any(type(v) is not int for v in vv.values()):
        raise ValueError('value is not int')


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
    return all(k in y and x[k] <= y[k] for k in x)
