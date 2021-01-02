import hashlib
import io
import json
import os, os.path
import shutil
import tempfile
import versionvector


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
    ValueError: hash tree is not dict
    >>> check_hash_tree(None)
    Traceback (most recent call last):
    ValueError: hash tree is not dict
    >>> check_hash_tree({'x', 'z'})
    Traceback (most recent call last):
    ValueError: hash tree is not dict

    Accepts empty dict:
    >>> check_hash_tree({})

    Fails if a key is not str:
    >>> check_hash_tree({'a': hash_bytes(b''), None: hash_bytes(b'')})
    Traceback (most recent call last):
    ValueError: hash tree key is not str
    >>> check_hash_tree({'a': hash_bytes(b''), 5: hash_bytes(b'')})
    Traceback (most recent call last):
    ValueError: hash tree key is not str

    Fails if a value is not str:
    >>> check_hash_tree({'a': hash_bytes(b''), 'b': None})
    Traceback (most recent call last):
    ValueError: hash tree value is not str
    >>> check_hash_tree({'a': hash_bytes(b''), 'x': b''})
    Traceback (most recent call last):
    ValueError: hash tree value is not str
    >>> check_hash_tree({'a': hash_bytes(b''), 'B': 5})
    Traceback (most recent call last):
    ValueError: hash tree value is not str

    Accepts a dict from str to str:
    >>> check_hash_tree({'R': hash_bytes(b'')})
    >>> check_hash_tree({'X': hash_bytes(b'x'), 'Y': hash_bytes(b'not')})
    """
    if type(hash_tree) is not dict:
        raise ValueError('hash tree is not dict')
    if any(type(k) is not str for k in hash_tree):
        raise ValueError('hash tree key is not str')
    if any(type(v) is not str for v in hash_tree.values()):
        raise ValueError('hash tree value is not str')


def check_meta_data(md):
    """
    Raises ValueError if md is not meta data.

    Fails if not dict:
    >>> check_meta_data('')
    Traceback (most recent call last):
    ValueError: meta data is not dict
    >>> check_meta_data(None)
    Traceback (most recent call last):
    ValueError: meta data is not dict
    >>> check_meta_data({'a'})
    Traceback (most recent call last):
    ValueError: meta data is not dict

    Fails if dict keys aren't exactly the expected ones:
    >>> check_meta_data({})
    Traceback (most recent call last):
    ValueError: invalid meta data keys
    >>> check_meta_data({'replicaID': None, 'versionVector': None})
    Traceback (most recent call last):
    ValueError: invalid meta data keys
    >>> check_meta_data({'replicaID': None, 'versionVector': None,
    ...     'hashTree': None, 'extraKey': None})
    Traceback (most recent call last):
    ValueError: invalid meta data keys
    >>> check_meta_data({'replicaID': None, 'versionVector': None,
    ...     'hashtree': None})
    Traceback (most recent call last):
    ValueError: invalid meta data keys

    Fails if replicaID is not str:
    >>> check_meta_data({'replicaID': 7, 'versionVector': {}, 'hashTree': {}})
    Traceback (most recent call last):
    ValueError: replicaID is not str

    Fails if versionVector is not a version vector:
    >>> check_meta_data({'replicaID': '', 'versionVector': 1, 'hashTree': {}})
    Traceback (most recent call last):
    ValueError: version vector is not dict

    Fails is hashTree is not a hash tree:
    >>> check_meta_data({'replicaID': '', 'versionVector': {}, 'hashTree': ''})
    Traceback (most recent call last):
    ValueError: hash tree is not dict

    Accepts valid meta data:
    >>> check_meta_data({'replicaID': 'MyReplica', 'versionVector': {'A': 4},
    ...     'hashTree': {'books/book': hash_bytes('content'.encode('utf-8'))}})
    """
    if type(md) is not dict:
        raise ValueError('meta data is not dict')
    if set(md.keys()) != {'replicaID', 'versionVector', 'hashTree'}:
        raise ValueError('invalid meta data keys')
    if type(md['replicaID']) is not str:
        raise ValueError('replicaID is not str')
    versionvector.check(md['versionVector'])
    check_hash_tree(md['hashTree'])


def write_meta_data(meta_data, directory, *, overwrite):
    """
    Write meta_data to META_FILE in directory.

    Fails for invalid meta data:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     write_meta_data({'replicaID': '', 'treeHash': {}}, d,
    ...         overwrite=True)
    Traceback (most recent call last):
    ValueError: invalid meta data keys

    >>> def make_md():
    ...     return {
    ...         'replicaID': 'Backup',
    ...         'versionVector': {'Laptop': 3, 'Backup': 2},
    ...         'hashTree': {
    ...             'school/homework': hash_bytes('essay'.encode('utf-8')),
    ...             'diary/January': hash_bytes('Vector-Sync'.encode('utf-8')),
    ...         },
    ...     }

    >>> def make_md_2():
    ...     return {
    ...         'replicaID': 'Alternative',
    ...         'versionVector': {'Desktop': 5},
    ...         'hashTree': {
    ...             'book': hash_bytes('text'.encode('utf-8')),
    ...         },
    ...     }

    >>> make_md() == make_md()
    True
    >>> make_md() is make_md()
    False

    >>> make_md_2() == make_md_2()
    True
    >>> make_md_2() is make_md_2()
    False

    >>> make_md() == make_md_2()
    False

    Throws an exception if the directory does not exist:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     write_meta_data(make_md(), os.path.join(d, 'child'),
    ...         overwrite=True)
    ... # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    FileNotFoundError

    Throws an exception if called for a file:
    >>> with tempfile.NamedTemporaryFile() as f:
    ...     write_meta_data(make_md(), f.name, overwrite=True)
    ... # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    NotADirectoryError

    Creates a new META_FILE in directory:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     write_meta_data(make_md(), d, overwrite=False)
    ...     with open(os.path.join(d, META_FILE), 'r', encoding='utf-8') as f:
    ...         json.load(f) == make_md()
    True

    Does not overwrite META_FILE with overwrite=False:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     write_meta_data(make_md(), d, overwrite=False)
    ...     try:
    ...         write_meta_data(make_md_2(), d, overwrite=False)
    ...     except FileExistsError:
    ...         print('caught FileExistsError')
    ...     with open(os.path.join(d, META_FILE), 'r', encoding='utf-8') as f:
    ...         json.load(f) == make_md()
    caught FileExistsError
    True

    Overwrites META_FILE with overwrite=True:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     write_meta_data(make_md(), d, overwrite=False)
    ...     with open(os.path.join(d, META_FILE), 'r', encoding='utf-8') as f:
    ...         json.load(f) == make_md()
    ...     write_meta_data(make_md_2(), d, overwrite=True)
    ...     with open(os.path.join(d, META_FILE), 'r', encoding='utf-8') as f:
    ...         json.load(f) == make_md_2()
    True
    True
    """
    check_meta_data(meta_data)
    meta_file_path = os.path.join(directory, META_FILE)
    mode = 'w' if overwrite else 'x'
    with open(meta_file_path, mode, encoding='utf-8') as f:
        json.dump(meta_data, f, indent=2, sort_keys=True)


def read_meta_data(directory):
    """
    Read meta data from META_FILE in directory.

    Throws an exception if the directory does not exist:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     read_meta_data(os.path.join(d, 'child'))
    ... # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    FileNotFoundError

    Throws an exception if called for a file:
    >>> with tempfile.NamedTemporaryFile() as f:
    ...     read_meta_data(f.name) # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    NotADirectoryError

    Throws an exception if META_FILE is missing:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     read_meta_data(d)  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    FileNotFoundError

    Throws an exception if the meta data is not valid:
    >>> partial_data = {'replicaID': 'R', 'versionVector': {'R': 1}}
    >>> with tempfile.TemporaryDirectory() as d:
    ...     with open(os.path.join(d, META_FILE), 'w', encoding='utf-8') as f:
    ...         json.dump(partial_data, f)
    ...     read_meta_data(d)
    Traceback (most recent call last):
    ValueError: invalid meta data keys

    >>> def make_md():
    ...     return {
    ...         'replicaID': 'Backup',
    ...         'versionVector': {'Laptop': 3, 'Backup': 2},
    ...         'hashTree': {
    ...             'school/project': hash_bytes('essay'.encode('utf-8')),
    ...             'diary/March': hash_bytes('Vector-Sync!'.encode('utf-8')),
    ...         },
    ...     }

    >>> make_md() == make_md()
    True
    >>> make_md() is make_md()
    False

    Loads an existing META_FILE:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     write_meta_data(make_md(), d, overwrite=False)
    ...     read_meta_data(d) == make_md()
    True
    """
    with open(os.path.join(directory, META_FILE), 'r', encoding='utf-8') as f:
        meta_data = json.load(f)
    check_meta_data(meta_data)
    return meta_data


def delete_up(path):
    """
    os.remove(path) then, if its parent is empty, os.removedirs(parent).

    Deletes the file at path and its empty immediate ancestors,
    but exactly which ancestors depends on how path is given.
    See the description above for the precise implementation.

    Throws an error if path does not exist:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     delete_up(os.path.join(d, 'child'))
    ... # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    FileNotFoundError

    Throws an error if called on a directory:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     e = os.path.join(d, 'e')
    ...     os.mkdir(e)
    ...     delete_up(e)  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    IsADirectoryError

    Does not remove the parent dir if it contains other files:
    >>> with tempfile.TemporaryDirectory() as a:
    ...     parent = os.path.join(a, 'b', 'c')
    ...     os.makedirs(parent)
    ...     with open(os.path.join(parent, 'x'), mode='x') as f:
    ...         pass
    ...     with open(os.path.join(parent, 'y'), mode='x') as f:
    ...         pass
    ...     delete_up(os.path.join(parent, 'x'))
    ...     os.path.exists(os.path.join(parent, 'x'))
    ...     os.path.exists(os.path.join(parent, 'y'))
    False
    True

    Removes empty immediate ancestors up to a non-empty ancestor:
    >>> with tempfile.TemporaryDirectory() as a:
    ...     with open(os.path.join(a, META_FILE), mode='x') as f:
    ...         pass
    ...     parent = os.path.join(a, 'c', 'd')
    ...     os.makedirs(parent)
    ...     child = os.path.join(parent, 'e')
    ...     with open(child, mode='x') as f:
    ...         pass
    ...     delete_up(child)
    ...     os.listdir(a)
    ['.vector-sync']
    """
    os.remove(path)
    parent = os.path.dirname(path)
    if parent and not os.listdir(parent):
        os.removedirs(parent)


def copy_down(src, dest):
    """
    Copy file src to dest, creating dest's parent if it does not exist.

    Copies a file to an existing directory:
    >>> with tempfile.TemporaryDirectory() as a:
    ...     with tempfile.TemporaryDirectory() as b:
    ...         x_path, y_path = os.path.join(a, 'x'), os.path.join(b, 'y')
    ...         msg = 's3cret'
    ...         with open(x_path, 'x', encoding='utf-8') as f:
    ...             f.write(msg) and None
    ...         copy_down(x_path, y_path)
    ...         with open(y_path, encoding='utf-8') as f:
    ...             f.read() == msg
    True

    Creates the new directory and its parents and copies the file to it:
    >>> with tempfile.TemporaryDirectory() as a:
    ...     with tempfile.TemporaryDirectory() as m:
    ...         x_path = os.path.join(a, 'x')
    ...         y_path = os.path.join(m, 'n', 'o', 'y')
    ...         msg = 'nest in nest'
    ...         with open(x_path, 'x', encoding='utf-8') as f:
    ...             f.write(msg) and None
    ...         copy_down(x_path, y_path)
    ...         with open(y_path, encoding='utf-8') as f:
    ...             f.read() == msg
    True

    Overwrites an existing file:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     x_path, y_path = os.path.join(d, 'x'), os.path.join(d, 'y')
    ...     x_msg, y_msg = 'hello', 'goodbye'
    ...     with open(x_path, 'x', encoding='utf-8') as f:
    ...         f.write(x_msg) and None
    ...     with open(y_path, 'x', encoding='utf-8') as f:
    ...         f.write(y_msg) and None
    ...     with open(y_path, encoding='utf-8') as f:
    ...         f.read()
    ...     copy_down(x_path, y_path)
    ...     with open(y_path, encoding='utf-8') as f:
    ...         f.read()
    'goodbye'
    'hello'
    """
    parent = os.path.dirname(dest)
    if parent:
        os.makedirs(parent, exist_ok=True)
    shutil.copyfile(src, dest)
