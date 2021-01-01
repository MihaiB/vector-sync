import hashlib
import io
import os, os.path
import tempfile


META_FILE_NAME = '.vector-sync'


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
    Compute the hexdigest of the bytes.

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
    Compute the hexdigest of the file contents.

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
