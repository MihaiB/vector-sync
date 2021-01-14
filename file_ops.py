import hashlib
import io
import json
import os, os.path


META_FILE = '.vector-sync'


def check_file_hashes(h):
    """
    Raise an exception if ‘h’ is not file_hashes.

    >>> check_file_hashes("bad")
    Traceback (most recent call last):
    ValueError: file hashes is not dict
    >>> check_file_hashes({3: ""})
    Traceback (most recent call last):
    ValueError: file hashes key is not str
    >>> check_file_hashes({"": {}})
    Traceback (most recent call last):
    ValueError: file hashes value is not str
    """
    if type(h) is not dict:
        raise ValueError('file hashes is not dict')
    if any(type(k) is not str for k in h):
        raise ValueError('file hashes key is not str')
    if any(type(v) is not str for v in h.values()):
        raise ValueError('file hashes value is not str')


def new_hash_obj():
    """
    Return a new hash object.

    Creates a new sha512 hash object:
    >>> new_hash_obj().name
    'sha512'
    """
    return hashlib.sha512()


def hash_file(filename):
    """Computes the hexdigest of the file content."""
    with open(filename, 'rb') as f:
        h = new_hash_obj()
        while True:
            b = f.read(io.DEFAULT_BUFFER_SIZE)
            if not b:
                return h.hexdigest()
            h.update(b)


def hash_file_tree(path):
    return _hash_file_tree(path, is_root=True)


def _hash_file_tree(tree_path, *, is_root):
    file_hashes = {}

    children = list(os.scandir(tree_path))

    for child in children:
        child_path = os.path.join(tree_path, child.name)

        if child.name == META_FILE:
            if is_root and child.is_file():
                continue
            raise Exception(f'forbidden tree item: {json.dumps(child_path)}')

        if child.is_file():
            file_hashes[child.name] = hash_file(child_path)
            continue

        if child.is_dir():
            for subpath, hash_val in _hash_file_tree(child_path,
                    is_root=False).items():
                file_hashes[os.path.join(child.name, subpath)] = hash_val

    if not file_hashes and not is_root:
        raise Exception(f'forbidden empty directory: {json.dumps(tree_path)}')

    check_file_hashes(file_hashes)
    return file_hashes
