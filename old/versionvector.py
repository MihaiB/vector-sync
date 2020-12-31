"""
A version vector maps replica IDs (strings) to int counters.
"""


def checkVersionVector(v):
    """
    Raises ValueError if v is not a version vector.

    Fails if not dictionary:
    >>> checkVersionVector('hi')
    Traceback (most recent call last):
    ValueError: not a dict
    >>> checkVersionVector(None)
    Traceback (most recent call last):
    ValueError: not a dict
    >>> checkVersionVector({'a', 'b'})
    Traceback (most recent call last):
    ValueError: not a dict

    Accepts empty dictionary:
    >>> checkVersionVector({})

    Fails is some key is not str:
    >>> checkVersionVector({'a': 1, 2: 2})
    Traceback (most recent call last):
    ValueError: key is not str
    >>> checkVersionVector({'a': 1, None: 1})
    Traceback (most recent call last):
    ValueError: key is not str

    Fails if some value is not int:
    >>> checkVersionVector({'a': 3, 'b': '4'})
    Traceback (most recent call last):
    ValueError: value is not int
    >>> checkVersionVector({'R': 0, 'S': None})
    Traceback (most recent call last):
    ValueError: value is not int
    >>> checkVersionVector({'i': 0, 'f': 2.0})
    Traceback (most recent call last):
    ValueError: value is not int

    Accepts a dict from str to int:
    >>> checkVersionVector({'X': 1})
    >>> checkVersionVector({'A': 0, 'B': 5})
    """
    if type(v) is not dict:
        raise ValueError('not a dict')
    if any(type(k) is not str for k in v):
        raise ValueError('key is not str')
    if any(type(v) is not int for v in v.values()):
        raise ValueError('value is not int')


def leq(x, y):
    """
    X ⊑ Y ⇔ every replica ID in X is in Y and its X counter ≤ its Y counter.

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
    >>> all(leq(x, x) for x in [{}, {'A': 1, 'Z': 26}])
    True
    """
    return all(k in y and x[k] <= y[k] for k in x)


def join(x, y):
    """
    X ⊔ Y has the union of X and Y's replica IDs.
    A replica ID's counter is the maximum of its counters in X and Y
    if it is present in both, else its counter from X or Y where it is present.

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
    """
    return {k: max(x.get(k, y.get(k)), y.get(k, x.get(k)))
            for k in x.keys() | y.keys()}


def makeIncrement(replicaID, versionVector):
    """
    Make a copy of versionVector and increment replicaID's counter
    or set it to 1 if it is absent.

    >>> makeIncrement('A', {})
    {'A': 1}
    >>> sorted(makeIncrement('K', {'A': 4, 'Z': 7}).items())
    [('A', 4), ('K', 1), ('Z', 7)]
    >>> sorted(makeIncrement('B', {'A': 3, 'B': 6, 'C': 12}).items())
    [('A', 3), ('B', 7), ('C', 12)]

    It returns a different dictionary:
    >>> all(makeIncrement('B', v) is not v for v in [{}, {'B': 5}])
    True

    The argument is not modified:
    >>> original = {'A': 2, 'Z': 1}
    >>> copy = dict(original)
    >>> sorted(makeIncrement('Z', original).items())
    [('A', 2), ('Z', 2)]
    >>> copy == original
    True
    """
    copy = dict(versionVector)
    copy[replicaID] = copy.get(replicaID, 0) + 1
    return copy
