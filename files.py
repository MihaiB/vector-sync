import copy
import hashlib
import io
import json
import os, os.path
import shutil
import tempfile
import versionvector


def newHashObj():
    """
    Return a new hash object.

    Creates a new sha512 hash object:
    >>> newHashObj().name
    'sha512'
    """
    return hashlib.sha512()


def hashBytes(b):
    """
    Computes the hexdigest of b.

    Computes the hash of a bytes object:
    >>> hashBytes(b'')
    'cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e'
    >>> hashBytes(b'hello\\n')
    'e7c22b994c59d9cf2b48e549b1e24666636045930d3da7c1acb299d1c3b7f931f94aae41edda2c2b207a36e10f8bcb8d45223e54878f5b316e7ce3b6bc019629'
    """
    h = newHashObj()
    h.update(b)
    return h.hexdigest()


def hashFile(fileName):
    """
    Returns hashBytes() for the contents of the file.

    Computes the hash of an empty file:
    >>> with tempfile.NamedTemporaryFile() as f:
    ...     hashFile(f.name)
    'cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e'

    Computes the hash of a non-empty file:
    >>> with tempfile.NamedTemporaryFile() as f:
    ...     f.write(b'test') and None
    ...     f.flush()
    ...     hashFile(f.name)
    'ee26b0dd4af7e749aa1a8ee3c10ae9923f618980772e473f8819a5d4940e0db27ac185f8a0e1d5f84f88bc887fd67b143732c304cc5fa9ad8e6f57f50028a8ff'

    Throws an exception if called with a directory:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     hashFile(d)  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    IsADirectoryError

    Throws an exception if the file does not exist:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     hashFile(os.path.join(d, 'file'))
    ... # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    FileNotFoundError

    Throws an exception if the nested file does not exist:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     hashFile(os.path.join(d, 'nested', 'file'))
    ... # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    FileNotFoundError
    """
    with open(fileName, 'rb') as f:
        h = newHashObj()
        while True:
            b = f.read(io.DEFAULT_BUFFER_SIZE)
            if not b:
                return h.hexdigest()
            h.update(b)


metaFile = '.vector-sync'


def getTreeHash(directory):
    """
    Map all files in the tree under directory to their hash.

    metaFile items and their subtrees are excluded.

    Error for missing tree:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     getTreeHash(os.path.join(d, 'a'))
    ... # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    FileNotFoundError
    >>> with tempfile.TemporaryDirectory() as d:
    ...     getTreeHash(os.path.join(d, 'a', 'b'))
    ... # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    FileNotFoundError

    Error for file:
    >>> with tempfile.NamedTemporaryFile() as f:
    ...     getTreeHash(f.name)
    ... # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    NotADirectoryError

    Error for descendant of a file:
    >>> with tempfile.NamedTemporaryFile() as f:
    ...     getTreeHash(os.path.join(f.name, 'x'))
    ... # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    NotADirectoryError
    """
    treeHash = {}
    for item in os.scandir(directory):
        if item.name == metaFile:
            continue
        path = os.path.join(directory, item.name)
        if item.is_file():
            treeHash[item.name] = hashFile(path)
        if item.is_dir():
            for subPath, hashVal in getTreeHash(path).items():
                treeHash[os.path.join(item.name, subPath)] = hashVal
    return treeHash


def checkTreeHash(treeHash):
    """
    Raises ValueError if treeHash is not a treeHash.

    Fails if not dict:
    >>> checkTreeHash('hi')
    Traceback (most recent call last):
    ValueError: not a dict
    >>> checkTreeHash(None)
    Traceback (most recent call last):
    ValueError: not a dict
    >>> checkTreeHash({'x', 'z'})
    Traceback (most recent call last):
    ValueError: not a dict

    Accepts empty dict:
    >>> checkTreeHash({})

    Fails if a key not str:
    >>> checkTreeHash({'a': hashBytes(b''), None: hashBytes(b'')})
    Traceback (most recent call last):
    ValueError: key not str
    >>> checkTreeHash({'a': hashBytes(b''), 5: hashBytes(b'')})
    Traceback (most recent call last):
    ValueError: key not str

    Fails if a value not str:
    >>> checkTreeHash({'a': hashBytes(b''), 'b': None})
    Traceback (most recent call last):
    ValueError: value not str
    >>> checkTreeHash({'a': hashBytes(b''), 'x': b''})
    Traceback (most recent call last):
    ValueError: value not str
    >>> checkTreeHash({'a': hashBytes(b''), 'B': 5})
    Traceback (most recent call last):
    ValueError: value not str

    Accepts a dict from str to str:
    >>> checkTreeHash({'R': hashBytes(b'')})
    >>> checkTreeHash({'X': hashBytes(b'x'), 'Y': hashBytes(b'not')})
    """
    if type(treeHash) is not dict:
        raise ValueError('not a dict')
    if any(type(k) is not str for k in treeHash):
        raise ValueError('key not str')
    if any(type(v) is not str for v in treeHash.values()):
        raise ValueError('value not str')


class MetaData:
    """
    A replica's metadata.


    Implements comparison: == and !=
    >>> MetaData('R', {'A': 2, 'B': 3}, {'users/jim': hashBytes(b'j'),
    ...     'etc/config': hashBytes(b'cfg')}) == MetaData('R',
    ...     {'A': 2, 'B': 3}, {'users/jim': hashBytes(b'j'),
    ...     'etc/config': hashBytes(b'cfg')})
    True
    >>> MetaData('R', {'A': 2, 'B': 3}, {'users/jim': hashBytes(b'j'),
    ...     'etc/config': hashBytes(b'cfg')}) != MetaData('R',
    ...     {'A': 2, 'B': 3}, {'users/jim': hashBytes(b'j'),
    ...     'etc/config': hashBytes(b'cfg')})
    False
    >>> MetaData('X', {'A': 1}, {}) == MetaData('Y', {'A': 1}, {})
    False
    >>> MetaData('X', {'A': 1}, {}) != MetaData('Y', {'A': 1}, {})
    True
    """

    def __init__(self, replicaID, versionVector, treeHash):
        if type(replicaID) is not str:
            raise ValueError('replicaID not str')
        versionvector.checkVersionVector(versionVector)
        checkTreeHash(treeHash)

        self.replicaID = replicaID
        self.versionVector = versionVector
        self.treeHash = treeHash

    def __eq__(self, other):
        def extract(md):
            return md.replicaID, md.versionVector, md.treeHash
        return extract(self) == extract(other)


def setMetaData(metaData, directory, overwrite=False):
    """
    Write metaData to metaFile in directory.

    Throws an exception if the directory does not exist:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     setMetaData(MetaData('a', {}, {}), os.path.join(d, 'child'))
    ... # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    FileNotFoundError

    Throws an exception if called for a file:
    >>> with tempfile.NamedTemporaryFile() as f:
    ...     setMetaData(MetaData('a', {}, {}), f.name)
    ... # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    NotADirectoryError

    >>> md = {'replicaID': 'Backup',
    ...     'versionVector': {'Laptop': 3, 'Backup': 2},
    ...     'treeHash': {
    ...     'school/homework': hashBytes('essay'.encode('utf-8')),
    ...     'diary/november': hashBytes('Vector-Sync!'.encode('utf-8'))}}
    >>> def makeMD():
    ...     return MetaData(**copy.deepcopy(md))

    Creates a new metaFile in directory:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     setMetaData(makeMD(), d)
    ...     with open(os.path.join(d, metaFile), 'r', encoding='utf-8') as f:
    ...         json.load(f) == md
    True

    Does not overwrite metaFile by default:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     setMetaData(MetaData('X', {'A': 3},
    ...     {'data': hashBytes(b'data')}), d)
    ...     try:
    ...         setMetaData(MetaData('Y', {'B': 4},
    ...         {'i': hashBytes(b'j')}), d)
    ...     except FileExistsError:
    ...         print('caught FileExistsError')
    ...     with open(os.path.join(d, metaFile), 'r', encoding='utf-8') as f:
    ...         json.load(f) == {
    ...             'replicaID': 'X',
    ...             'versionVector': {'A': 3},
    ...             'treeHash': {'data': hashBytes(b'data')}}
    caught FileExistsError
    True

    Overwrites metaFile in directory with overwrite=True:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     setMetaData(MetaData('X', {'Y':1},
    ...         {'trash': hashBytes('bin'.encode('utf-8'))}), d)
    ...     metaFilePath = os.path.join(d, metaFile)
    ...     with open(metaFilePath, 'r', encoding='utf-8') as f:
    ...         json.load(f) == {
    ...             'replicaID': 'X',
    ...             'versionVector': {'Y': 1},
    ...             'treeHash': {'trash': hashBytes('bin'.encode('utf-8'))}}
    ...     setMetaData(makeMD(), d, overwrite=True)
    ...     with open(metaFilePath, 'r', encoding='utf-8') as f:
    ...         json.load(f) == md
    True
    True
    """
    mode = 'w' if overwrite else 'x'
    with open(os.path.join(directory, metaFile), mode, encoding='utf-8') as f:
        json.dump({
            'replicaID': metaData.replicaID,
            'versionVector': metaData.versionVector,
            'treeHash': metaData.treeHash,
        }, f)


def getMetaData(directory):
    """
    Get metaData from metaFile in directory.

    Throws an exception if the directory does not exist:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     getMetaData(os.path.join(d, 'child'))
    ... # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    FileNotFoundError

    Throws an exception if called for a file:
    >>> with tempfile.NamedTemporaryFile() as f:
    ...     getMetaData(f.name) # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    NotADirectoryError

    Throws an exception if metaFile is missing:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     getMetaData(d)  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    FileNotFoundError

    Throws an exception if some fields are missing from the metaFile:
    >>> partialData = {'replicaID': 'R', 'versionVector': {'R': 1}}
    >>> with tempfile.TemporaryDirectory() as d:
    ...     with open(os.path.join(d, metaFile), 'w', encoding='utf-8') as f:
    ...         json.dump(partialData, f)
    ...     getMetaData(d)
    Traceback (most recent call last):
    KeyError: 'treeHash'

    >>> r = 'Backup'
    >>> v = {'Laptop': 3, 'Backup': 2}
    >>> t = { 'school/project': hashBytes('essay'.encode('utf-8')),
    ...     'diary/november': hashBytes('Vector-Sync!'.encode('utf-8'))}

    Loads an existing metaFile:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     setMetaData(MetaData(r, copy.deepcopy(v), copy.deepcopy(t)), d)
    ...     readMD = getMetaData(d)
    ...     (readMD.replicaID, readMD.versionVector,
    ...         readMD.treeHash) == (r, v, t)
    True
    """
    with open(os.path.join(directory, metaFile), 'r', encoding='utf-8') as f:
        data = json.load(f)
    return MetaData(data['replicaID'], data['versionVector'],
            data['treeHash'])


def deleteUp(path):
    """
    os.remove(path) then, if path has a parent which is empty,
    os.removedirs(parent).

    Deletes the file at path and its empty immediate ancestors,
    but exactly which ancestors depends on how path is given.
    See the description above for the precise implementation.

    Throws an error if path does not exist:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     deleteUp(os.path.join(d, 'e'))  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    FileNotFoundError

    Throws an error if called on a directory:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     e = os.path.join(d, 'e')
    ...     os.mkdir(e)
    ...     deleteUp(e)  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    IsADirectoryError

    Does not remove parent dir if it contains other files:
    >>> with tempfile.TemporaryDirectory() as a:
    ...     parent = os.path.join(a, 'b', 'c')
    ...     os.makedirs(parent)
    ...     with open(os.path.join(parent, 'x'), mode='x') as f:
    ...         pass
    ...     with open(os.path.join(parent, 'y'), mode='x') as f:
    ...         pass
    ...     deleteUp(os.path.join(parent, 'x'))
    ...     os.path.exists(os.path.join(parent, 'y'))
    True

    Removes empty immediate ancestors up to a non-empty ancestor:
    >>> with tempfile.TemporaryDirectory() as a:
    ...     with open(os.path.join(a, metaFile), mode='x') as f:
    ...         pass
    ...     parent = os.path.join(a, 'c', 'd')
    ...     os.makedirs(parent)
    ...     child = os.path.join(parent, 'e')
    ...     with open(child, mode='x') as f:
    ...         pass
    ...     deleteUp(child)
    ...     os.listdir(a)
    ['.vector-sync']
    """
    os.remove(path)
    parent = os.path.dirname(path)
    if parent and not os.listdir(parent):
        os.removedirs(parent)


def copyDown(src, dest):
    """
    Copies file src to dest, creating dest's parent directory if missing.

    Copies a file to an existing directory:
    >>> with tempfile.TemporaryDirectory() as a:
    ...     with tempfile.TemporaryDirectory() as b:
    ...         xPath, yPath = os.path.join(a, 'x'), os.path.join(b, 'y')
    ...         msg = 's3cret'
    ...         with open(xPath, 'x', encoding='utf-8') as f:
    ...             f.write(msg) and None
    ...         copyDown(xPath, yPath)
    ...         with open(yPath, encoding='utf-8') as f:
    ...             f.read()
    's3cret'

    Creates the new directory and its parents and copies the file to it:
    >>> with tempfile.TemporaryDirectory() as a:
    ...     with tempfile.TemporaryDirectory() as m:
    ...         xPath = os.path.join(a, 'x')
    ...         yPath = os.path.join(m, 'n', 'o', 'y')
    ...         msg = 'nest in nest'
    ...         with open(xPath, 'x', encoding='utf-8') as f:
    ...             f.write(msg) and None
    ...         copyDown(xPath, yPath)
    ...         with open(yPath, encoding='utf-8') as f:
    ...             f.read()
    'nest in nest'

    Overwrites an existing file:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     xPath, yPath = os.path.join(d, 'x'), os.path.join(d, 'y')
    ...     xMsg, yMsg = 'hello', 'goodbye'
    ...     with open(xPath, 'x', encoding='utf-8') as f:
    ...         f.write(xMsg) and None
    ...     with open(yPath, 'x', encoding='utf-8') as f:
    ...         f.write(yMsg) and None
    ...     with open(yPath, encoding='utf-8') as f:
    ...         f.read()
    ...     copyDown(xPath, yPath)
    ...     with open(yPath, encoding='utf-8') as f:
    ...         f.read()
    'goodbye'
    'hello'
    """
    parent = os.path.dirname(dest)
    if parent:
        os.makedirs(parent, exist_ok=True)
    shutil.copyfile(src, dest)


class TreeChange:
    """
    Describes which paths must be changed in a tree to arrive at another.

    Does not accept positional args:
    >>> TreeChange(set(), set(), set())
    Traceback (most recent call last):
    TypeError: __init__() takes 1 positional argument but 4 were given

    Does not accept positional args in addition to the keyword args:
    >>> TreeChange(set(), delete=set(), overwrite=set(), add=set())
    Traceback (most recent call last):
    TypeError: __init__() takes 1 positional argument but 2 positional arguments (and 3 keyword-only arguments) were given

    Does not accept additional keyword args:
    >>> TreeChange(delete=set(), overwrite=set(), add=set(), myarg=set())
    Traceback (most recent call last):
    TypeError: __init__() got an unexpected keyword argument 'myarg'

    Raises an exception if any item is not a set or any elment is not a str:
    >>> TreeChange(delete=[], overwrite=set(), add=set())
    Traceback (most recent call last):
    ValueError: not a set
    >>> TreeChange(delete=set(), overwrite=None, add=set())
    Traceback (most recent call last):
    ValueError: not a set
    >>> TreeChange(delete=set(), overwrite=set(), add=())
    Traceback (most recent call last):
    ValueError: not a set
    >>> TreeChange(delete={'a', 3}, overwrite=set(), add=set())
    Traceback (most recent call last):
    ValueError: not a str
    >>> TreeChange(delete=set(), overwrite={'x', None}, add=set())
    Traceback (most recent call last):
    ValueError: not a str
    >>> TreeChange(delete=set(), overwrite=set(), add={'a', 'b', 1, 'c'})
    Traceback (most recent call last):
    ValueError: not a str

    Accepts empty sets:
    >>> tc = TreeChange(delete=set(), overwrite=set(), add=set())
    >>> (tc.delete, tc.overwrite, tc.add) == (set(), set(), set())
    True

    Accepts sets of strings:
    >>> tc = TreeChange(delete={'bin'}, overwrite={'change', 'me'},
    ...     add={'create', 'this'})
    >>> (tc.delete, tc.overwrite, tc.add) == ({'bin'}, {'change', 'me'},
    ...     {'create', 'this'})
    True

    Implements comparison: == and !=
    >>> TreeChange(delete={'del'}, overwrite={'changed'},
    ...     add={'add', 'me'}) == TreeChange(delete={'del'},
    ...     overwrite={'changed'}, add={'add', 'me'})
    True
    >>> TreeChange(delete={'del'}, overwrite={'changed'},
    ...     add={'add', 'me'}) != TreeChange(delete={'del'},
    ...     overwrite={'changed'}, add={'add', 'me'})
    False
    >>> TreeChange(delete={'a'}, overwrite=set(), add=set()) == TreeChange(
    ...     delete={'b'}, overwrite=set(), add=set())
    False
    >>> TreeChange(delete={'a'}, overwrite=set(), add=set()) != TreeChange(
    ...     delete={'b'}, overwrite=set(), add=set())
    True
    """

    def __init__(self, *, delete, overwrite, add):
        for xs in (delete, overwrite, add):
            if type(xs) is not set:
                raise ValueError('not a set')
            if any(type(x) is not str for x in xs):
                raise ValueError('not a str')

        self.delete, self.overwrite, self.add = delete, overwrite, add

    def __eq__(self, other):
        def extract(tc):
            return tc.delete, tc.overwrite, tc.add
        return extract(self) == extract(other)


def getTreeChange(start, end):
    """
    Compute the TreeChange between the two trees.

    >>> tc = getTreeChange({},
    ...     {'a': hashBytes(b''), 'x': hashBytes(b'X')})
    >>> (tc.delete, tc.overwrite, tc.add) == (set(), set(), {'a', 'x'})
    True

    >>> tc = getTreeChange({'1': hashBytes(b'1'), '9': hashBytes(b'0')},
    ...     {})
    >>> (tc.delete, tc.overwrite, tc.add) == ({'1', '9'}, set(), set())
    True

    >>> tc = getTreeChange({'task': hashBytes(b'dishes'),
    ...     'v': hashBytes(b'1'), 'trash': hashBytes(b't'),
    ...     'bin': hashBytes(b'b'), 'i': hashBytes(b'')},
    ...     {'task': hashBytes(b'laundry'), 'v': hashBytes(b'2'),
    ...     'prj': hashBytes(b''), 'w': hashBytes(b''),
    ...     'i': hashBytes(b'')})
    >>> (tc.delete, tc.overwrite, tc.add) == ({'trash', 'bin'}, {'task', 'v'},
    ...     {'prj', 'w'})
    True
    """
    for th in (start, end):
        checkTreeHash(th)

    delete = {k for k in start if k not in end}
    overwrite = {k for k in start if k in end and start[k] != end[k]}
    add = {k for k in end if k not in start}

    return TreeChange(delete=delete, overwrite=overwrite, add=add)


def confirmTreeChange(treeChange, replicaID):
    """
    Ask the user to confirm the change and return bool.

    Returns True without asking for confirmation if the change is empty.
    """
    found = False
    for pathSet, title, char in (
            (treeChange.add,        'New',      '+'),
            (treeChange.delete,     'Deleted',  '−'),
            (treeChange.overwrite,  'Changed',  '≠'),
            ):
        if not pathSet:
            continue
        found = True
        print('•', title, 'files:')
        for path in sorted(pathSet):
            print(char, path)
        print()

    if not found:
        return True

    return input('Make changes to ' + replicaID + '? [y/N] ').upper() == 'Y'


def applyTreeChange(treeChange, *, src, dest):
    """
    Apply the TreeChange to dest, reading files from src.

    It does not accept additional positional arguments:
    >>> applyTreeChange(TreeChange(delete=set(), overwrite=set(), add=set()),
    ...     None, src='s', dest='d')
    Traceback (most recent call last):
    TypeError: applyTreeChange() takes 1 positional argument but 2 positional arguments (and 2 keyword-only arguments) were given
    """
    for path in treeChange.delete:
        deleteUp(os.path.join(dest, path))
    for items in (treeChange.overwrite, treeChange.add):
        for path in items:
            copyDown(os.path.join(src, path), os.path.join(dest, path))
