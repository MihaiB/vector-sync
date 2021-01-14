import hashlib
import io
import json
import os, os.path
import versionvectors


META_FILE = '.vector-sync'


def check_file_hashes(h):
    """
    Raise an exception if ‘h’ is not file_hashes.

    >>> check_file_hashes('bad')
    Traceback (most recent call last):
    ValueError: file hashes is not dict
    >>> check_file_hashes({3: ''})
    Traceback (most recent call last):
    ValueError: file hashes key is not str
    >>> check_file_hashes({'': {}})
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


def check_meta_data(md):
    """
    Raise an exception if md is not meta data.

    >>> check_meta_data(None)
    Traceback (most recent call last):
    ValueError: meta data is not dict
    >>> check_meta_data({'bad': {}, 'keys': ''})
    Traceback (most recent call last):
    ValueError: invalid meta data keys
    >>> check_meta_data({'id': 7, 'version_vector': {}, 'file_hashes': {}})
    Traceback (most recent call last):
    ValueError: meta data id is not str
    >>> check_meta_data({'id': 'A', 'version_vector': {3}, 'file_hashes': {}})
    Traceback (most recent call last):
    ValueError: version vector is not dict
    >>> check_meta_data({'id': 'A', 'version_vector': {}, 'file_hashes': '?'})
    Traceback (most recent call last):
    ValueError: file hashes is not dict

    >>> check_meta_data({'id': 'A', 'version_vector': {}, 'file_hashes': {}})
    """
    if type(md) is not dict:
        raise ValueError('meta data is not dict')
    if set(md.keys()) != {'id', 'version_vector', 'file_hashes'}:
        raise ValueError('invalid meta data keys')
    if type(md['id']) is not str:
        raise ValueError('meta data id is not str')
    versionvectors.check(md['version_vector'])
    check_file_hashes(md['file_hashes'])


def write_meta_data(md, filepath):
    check_meta_data(md)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(md, f, indent=2, sort_keys=True)


def read_meta_data(filepath):
    with open(filepath, encoding='utf-8') as f:
        md = json.load(f)
    check_meta_data(md)
    return md


def init_file_tree(*, treepath, tree_id):
    filepath = os.path.join(treepath, META_FILE)
    # error out if the file already exists
    with open(filepath, 'x', encoding='utf-8') as f:
        pass

    md = {
        'id': tree_id,
        'version_vector': {},
        'file_hashes': {},
    }
    check_meta_data(md)
    write_meta_data(md, filepath)

    print(f'Initialized {json.dumps(tree_id)} in {json.dumps(treepath)}.')
