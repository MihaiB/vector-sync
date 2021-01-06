import json
import versionvectors


def check_file_hashes(h):
    """
    >>> check_file_hashes("bad")
    Traceback (most recent call last):
    ValueError: file hashes are not dict
    >>> check_file_hashes({3: ""})
    Traceback (most recent call last):
    ValueError: file hashes key is not str
    >>> check_file_hashes({"": {}})
    Traceback (most recent call last):
    ValueError: file hashes value is not str
    """
    if type(h) is not dict:
        raise ValueError('file hashes are not dict')
    if any(type(k) is not str for k in h):
        raise ValueError('file hashes key is not str')
    if any(type(v) is not str for v in h.values()):
        raise ValueError('file hashes value is not str')


def check_meta_data(md):
    """
    >>> check_meta_data(None)
    Traceback (most recent call last):
    ValueError: meta data is not dict
    >>> check_meta_data({'bad': {}, 'keys': ""})
    Traceback (most recent call last):
    ValueError: invalid meta data keys
    >>> check_meta_data({'id': 7, 'version_vector': {}, 'file_hashes': {}})
    Traceback (most recent call last):
    ValueError: meta data id is not str
    >>> check_meta_data({'id': "A", 'version_vector': {3}, 'file_hashes': {}})
    Traceback (most recent call last):
    ValueError: version vector is not dict
    >>> check_meta_data({'id': "A", 'version_vector': {}, 'file_hashes': '?'})
    Traceback (most recent call last):
    ValueError: file hashes are not dict
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
