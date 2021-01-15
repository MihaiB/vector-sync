import hashlib
import io
import json
import os, os.path
import shutil
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


def delete_up(filepath):
    """Delete the file and all empty parent directories."""
    path = os.path.realpath(filepath)
    del filepath

    os.remove(path)
    # Because ‘path’ is an absolute not a relative path
    # ‘parent’ won't be the empty string.
    parent = os.path.dirname(path)
    if not os.listdir(parent):
        os.removedirs(parent)


def copy_down(src_file, dest_file):
    """Copy src_file to dest_file creating dest_file's parent if absent."""
    dest_file = os.path.realpath(dest_file)
    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
    shutil.copyfile(src_file, dest_file)


def check_tree_status(ts):
    """
    Raise an exception if ts is not a tree status.

    >>> check_tree_status([])
    Traceback (most recent call last):
    ValueError: tree status is not dict
    >>> check_tree_status({'id': 'A', 'hello': 'world'})
    Traceback (most recent call last):
    ValueError: invalid tree status keys
    >>> check_tree_status({'path': 5, 'id': 'A', 'pre_vv': {},
    ...     'known_hashes': {}, 'disk_hashes': {}, 'post_vv': {}})
    Traceback (most recent call last):
    ValueError: tree status path is not str
    >>> check_tree_status({'path': '.', 'id': None, 'pre_vv': {},
    ...     'known_hashes': {}, 'disk_hashes': {}, 'post_vv': {}})
    Traceback (most recent call last):
    ValueError: tree status id is not str
    >>> check_tree_status({'path': '.', 'id': 'A', 'pre_vv': 5,
    ...     'known_hashes': {}, 'disk_hashes': {}, 'post_vv': {}})
    Traceback (most recent call last):
    ValueError: version vector is not dict
    >>> check_tree_status({'path': '.', 'id': 'A', 'pre_vv': {},
    ...     'known_hashes': 0, 'disk_hashes': {}, 'post_vv': {}})
    Traceback (most recent call last):
    ValueError: file hashes is not dict
    >>> check_tree_status({'path': '.', 'id': 'A', 'pre_vv': {},
    ...     'known_hashes': {}, 'disk_hashes': {1: ''}, 'post_vv': {}})
    Traceback (most recent call last):
    ValueError: file hashes key is not str
    >>> check_tree_status({'path': '.', 'id': 'A', 'pre_vv': {},
    ...     'known_hashes': {}, 'disk_hashes': {}, 'post_vv': {'A': 'B'}})
    Traceback (most recent call last):
    ValueError: version vector value is not int

    >>> check_tree_status({'path': '.', 'id': 'A', 'pre_vv': {},
    ...     'known_hashes': {}, 'disk_hashes': {}, 'post_vv': {}})
    """
    if type(ts) is not dict:
        raise ValueError('tree status is not dict')
    if set(ts.keys()) != {'path', 'id', 'pre_vv',
            'known_hashes', 'disk_hashes', 'post_vv'}:
        raise ValueError('invalid tree status keys')
    if type(ts['path']) is not str:
        raise ValueError('tree status path is not str')
    if type(ts['id']) is not str:
        raise ValueError('tree status id is not str')
    versionvectors.check(ts['pre_vv'])
    check_file_hashes(ts['known_hashes'])
    check_file_hashes(ts['disk_hashes'])
    versionvectors.check(ts['post_vv'])


def read_tree_status(path):
    md = read_meta_data(os.path.join(path, META_FILE))
    disk_hashes = hash_file_tree(path)
    post_vv = md['version_vector'] if disk_hashes == md['file_hashes'] \
            else versionvectors.advance(md['id'], md['version_vector'])
    ts = {
        'path': path,
        'id': md['id'],
        'pre_vv': md['version_vector'],
        'known_hashes': md['file_hashes'],
        'disk_hashes': disk_hashes,
        'post_vv': post_vv,
    }
    check_tree_status(ts)
    return ts


def confirm(prompt):
    """Asks ‘prompt [y/N] ’ and returns bool."""
    answer = input(prompt + ' [y/N] ')
    return answer.lower() == 'y'


def ensure_meta_data(version_vector, file_hashes, tree_status):
    """Returns true if it wrote the meta data, false if it didn't."""
    versionvectors.check(version_vector)
    check_file_hashes(file_hashes)
    check_tree_status(tree_status)

    if (version_vector == tree_status['pre_vv']
            and file_hashes == tree_status['known_hashes']):
        return False

    md = {
            'id': tree_status['id'],
            'version_vector': version_vector,
            'file_hashes': file_hashes,
    }
    check_meta_data(md)

    write_meta_data(md, os.path.join(tree_status['path'], META_FILE))
    return True


def format_tree_change(a, z):
    """Return the change between file hashes ‘a’ and ‘z’ as a string."""
    check_file_hashes(a)
    check_file_hashes(z)

    add_paths = {p for p in z if p not in a}
    del_paths = {p for p in a if p not in z}
    overwrite_paths = {p for p in a if p in z and a[p] != z[p]}

    lines = []
    for paths, word, char in (
            (add_paths, 'Add', '+'),
            (del_paths, 'Delete', '-'),
            (overwrite_paths, 'Overwrite', '≠'),
            ):
        if not paths:
            continue
        if lines:
            lines.append('')
        lines.append(f'• {word}:')
        for p in sorted(paths):
            lines.append(f'{char} {json.dumps(p)}')

    return '\n'.join(lines)
