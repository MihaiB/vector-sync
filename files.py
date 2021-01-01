import hashlib
import io
import os, os.path
import tempfile


META_FILE = '.vector-sync'


def new_hash_obj():
    """
    Return a new hash object.

    Creates a new sha512 hash object:
    >>> new_hash_obj().name
    'sha512'
    """
    return hashlib.sha512()


def hash_bytes(b):
    """
    Computes the hexdigest of the bytes.

    Computes the hash of a bytes object:
    >>> hash_bytes(b'')
    'cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e'
    >>> hash_bytes(b'hello\\n')
    'e7c22b994c59d9cf2b48e549b1e24666636045930d3da7c1acb299d1c3b7f931f94aae41edda2c2b207a36e10f8bcb8d45223e54878f5b316e7ce3b6bc019629'
    """
    h = new_hash_obj()
    h.update(b)
    return h.hexdigest()


def hash_file(filename):
    """
    Computes the hexdigest of the file content.

    Computes the hash of an empty file:
    >>> with tempfile.NamedTemporaryFile() as f:
    ...     hash_file(f.name)
    'cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e'

    Computes the hash of a non-empty file:
    >>> with tempfile.NamedTemporaryFile() as f:
    ...     f.write(b'test') and None
    ...     f.flush()
    ...     hash_file(f.name)
    'ee26b0dd4af7e749aa1a8ee3c10ae9923f618980772e473f8819a5d4940e0db27ac185f8a0e1d5f84f88bc887fd67b143732c304cc5fa9ad8e6f57f50028a8ff'

    Throws an exception if called with a directory:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     hash_file(d)  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    IsADirectoryError

    Throws an exception if the file does not exist:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     hash_file(os.path.join(d, 'file'))
    ... # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    FileNotFoundError

    Throws an exception if the file's parent dir does not exist:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     hash_file(os.path.join(d, 'nested', 'file'))
    ... # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    FileNotFoundError
    """
    h = new_hash_obj()

    with open(filename, 'rb') as f:
        while True:
            b = f.read(io.DEFAULT_BUFFER_SIZE)
            if not b:
                break
            h.update(b)

    return h.hexdigest()


def hash_file_tree(tree_path):
    """
    Map all files in the tree to their hash.

    META_FILE descendants are excluded.

    Error for missing tree:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     hash_file_tree(os.path.join(d, 'a'))
    ... # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    FileNotFoundError
    >>> with tempfile.TemporaryDirectory() as d:
    ...     hash_file_tree(os.path.join(d, 'a', 'b'))
    ... # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    FileNotFoundError

    Error for file:
    >>> with tempfile.NamedTemporaryFile() as f:
    ...     hash_file_tree(f.name)
    ... # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    NotADirectoryError

    Error for descendant of a file:
    >>> with tempfile.NamedTemporaryFile() as f:
    ...     hash_file_tree(os.path.join(f.name, 'x'))
    ... # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    NotADirectoryError
    """
    hash_tree = {}
    for item in os.scandir(tree_path):
        if item.name == META_FILE:
            continue
        item_path = os.path.join(tree_path, item.name)
        if item.is_file():
            hash_tree[item.name] = hash_file(item_path)
        if item.is_dir():
            hash_tree.update({os.path.join(item.name, k): v
                for k, v in hash_file_tree(item_path).items()})
    return hash_tree


def check_hash_tree(hash_tree):
    """
    Raises ValueError if hash_tree is not a hash tree.

    Fails if not dict:
    >>> check_hash_tree('hi')
    Traceback (most recent call last):
    ValueError: not a dict
    >>> check_hash_tree(None)
    Traceback (most recent call last):
    ValueError: not a dict
    >>> check_hash_tree({'x', 'z'})
    Traceback (most recent call last):
    ValueError: not a dict

    Accepts empty dict:
    >>> check_hash_tree({})

    Fails if a key is not str:
    >>> check_hash_tree({'a': hash_bytes(b''), None: hash_bytes(b'')})
    Traceback (most recent call last):
    ValueError: key not str
    >>> check_hash_tree({'a': hash_bytes(b''), 5: hash_bytes(b'')})
    Traceback (most recent call last):
    ValueError: key not str

    Fails if a value is not str:
    >>> check_hash_tree({'a': hash_bytes(b''), 'b': None})
    Traceback (most recent call last):
    ValueError: value not str
    >>> check_hash_tree({'a': hash_bytes(b''), 'x': b''})
    Traceback (most recent call last):
    ValueError: value not str
    >>> check_hash_tree({'a': hash_bytes(b''), 'B': 5})
    Traceback (most recent call last):
    ValueError: value not str

    Accepts a dict from str to str:
    >>> check_hash_tree({'R': hash_bytes(b'')})
    >>> check_hash_tree({'X': hash_bytes(b'x'), 'Y': hash_bytes(b'not')})
    """
    if type(hash_tree) is not dict:
        raise ValueError('not a dict')
    if any(type(k) is not str for k in hash_tree):
        raise ValueError('key not str')
    if any(type(v) is not str for v in hash_tree.values()):
        raise ValueError('value not str')
