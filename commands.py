import files
import os, os.path
import tempfile
import versionvector


def init(ID):
    files.setMetaData(files.MetaData(ID, {}, {}), '.')
    print('Initialized new empty replica', ID + '.')


class SyncInput:
    """
    A replica's input to the sync operation.
    """

    def __init__(self, *, replicaRoot, replicaID, versionVector, treeHash):
        versionvector.checkVersionVector(versionVector)
        files.checkTreeHash(treeHash)

        self.replicaRoot = replicaRoot
        self.replicaID = replicaID
        self.versionVector = versionVector
        self.treeHash = treeHash

    def __eq__(self, other):
        def extract(si):
            return si.replicaRoot, si.replicaID, si.versionVector, si.treeHash
        return extract(self) == extract(other)


def getSyncInput(replicaRoot):
    """
    Get a replica's SyncInput.

    The replica's ID is incremented in versionVector if the tree hash differs
    from the MetaData in metaFile.

    Raises an exception if the directory does not exist:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     getSyncInput(os.path.join(d, 'no-such-dir'))
    ... # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    FileNotFoundError

    Returns the existing version vector if disk tree is the same as meta data:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     files.setMetaData(files.MetaData('D', {'A': 1},
    ...         {'hobby': files.hashBytes('code'.encode('utf-8'))}), d)
    ...     with open(os.path.join(d, 'hobby'), 'x') as f:
    ...         f.write('code') and None
    ...     getSyncInput(d) == SyncInput(replicaRoot=d, replicaID='D',
    ...         versionVector={'A': 1},
    ...         treeHash={'hobby': files.hashBytes('code'.encode('utf-8'))})
    True

    Increments ReplicaID in version vector if disk tree changed from meta data:
    >>> with tempfile.TemporaryDirectory() as d:
    ...     files.setMetaData(files.MetaData('D', {'A': 1},
    ...         {'hobby': files.hashBytes('code'.encode('utf-8'))}), d)
    ...     with open(os.path.join(d, 'hobby'), 'x') as f:
    ...         f.write('decode') and None
    ...     getSyncInput(d) == SyncInput(replicaRoot=d, replicaID='D',
    ...         versionVector={'A': 1, 'D': 1},
    ...         treeHash={
    ...             'hobby': files.hashBytes('decode'.encode('utf-8'))})
    True
    """
    metaData = files.getMetaData(replicaRoot)
    treeHash = files.getTreeHash(replicaRoot)
    vv = metaData.versionVector
    if treeHash != metaData.treeHash:
        vv = versionvector.makeIncrement(metaData.replicaID, vv)
    return SyncInput(replicaRoot=replicaRoot, replicaID=metaData.replicaID,
            versionVector=vv, treeHash=treeHash)


class SyncResult:
    """
    Version vector and tree hash (with its root) for a successful sync.

    Raises an exception if a parameter has incorrect type:
    >>> SyncResult({'R': '3'}, {'f': files.hashBytes(b'')}, 'some/path')
    Traceback (most recent call last):
    ValueError: value is not int
    >>> SyncResult({'R': 3}, {'f': b''}, 'some/path')
    Traceback (most recent call last):
    ValueError: value not str
    >>> SyncResult({'R': 3}, {'f': files.hashBytes(b'')}, 8)
    Traceback (most recent call last):
    ValueError: treeRoot not str

    Accepts parameters of correct types:
    >>> sr = SyncResult({'R': 3}, {'f': files.hashBytes(b'')}, 'some/path')
    >>> (sr.versionVector, sr.treeHash, sr.treeRoot) == ({'R': 3},
    ...     {'f': files.hashBytes(b'')}, 'some/path')
    True
    """

    def __init__(self, versionVector, treeHash, treeRoot):
        versionvector.checkVersionVector(versionVector)
        files.checkTreeHash(treeHash)
        if type(treeRoot) is not str:
            raise ValueError('treeRoot not str')

        self.versionVector = versionVector
        self.treeHash = treeHash
        self.treeRoot = treeRoot

    def __eq__(self, other):
        def extract(sr):
            return sr.versionVector, sr.treeHash, sr.treeRoot
        return extract(self) == extract(other)


def getSyncResult(inA, inB):
    """
    Return the SyncResult for 2 SyncInputs or throw an exception.

    With same trees:
    >>> getSyncResult(
    ...     SyncInput(replicaRoot='i/one', replicaID='X',
    ...         versionVector={'A': 3},
    ...         treeHash={'q': files.hashBytes(b'Q'),
    ...         'w/q': files.hashBytes(b'qw')}),
    ...     SyncInput(replicaRoot='j/two', replicaID='Y',
    ...         versionVector={'B': 2},
    ...         treeHash={'q': files.hashBytes(b'Q'),
    ...         'w/q': files.hashBytes(b'qw')})
    ...     ) == SyncResult({'A': 3, 'B': 2}, {'q': files.hashBytes(b'Q'),
    ...         'w/q': files.hashBytes(b'qw')}, 'i/one')
    True

    Else, same input vv:
    >>> getSyncResult(
    ...     SyncInput(replicaRoot='a', replicaID='A',
    ...         versionVector={'C': 1},
    ...         treeHash={'f': files.hashBytes(b'a')}),
    ...     SyncInput(replicaRoot='b', replicaID='B',
    ...         versionVector={'C': 1},
    ...         treeHash={'f': files.hashBytes(b'b')}))
    Traceback (most recent call last):
    Exception: refusing to sync: A and B have diverged

    Else, A before B:
    >>> getSyncResult(
    ...     SyncInput(replicaRoot='path/to/a', replicaID='V',
    ...         versionVector={'R': 1},
    ...         treeHash={'f': files.hashBytes(b'')}),
    ...     SyncInput(replicaRoot='path/to/b', replicaID='W',
    ...         versionVector={'R': 2},
    ...         treeHash={'g': files.hashBytes(b'g')})
    ...     ) == SyncResult({'R': 2}, {'g': files.hashBytes(b'g')},
    ...         'path/to/b')
    True

    Else, B before A:
    >>> getSyncResult(
    ...     SyncInput(replicaRoot='nfs/mount', replicaID='net',
    ...         versionVector={'Y': 5},
    ...         treeHash={'a': files.hashBytes(b'a')}),
    ...     SyncInput(replicaRoot='hdd/local', replicaID='sda',
    ...         versionVector={'Y': 3},
    ...         treeHash={'b': files.hashBytes(b'b')})
    ...     ) == SyncResult({'Y': 5},
    ...         {'a': files.hashBytes(b'a')}, 'nfs/mount')
    True

    Else:
    >>> getSyncResult(
    ...     SyncInput(replicaRoot='a', replicaID='A',
    ...     versionVector={'M': 1}, treeHash={'a': files.hashBytes(b'')}),
    ...     SyncInput(replicaRoot='b', replicaID='B',
    ...     versionVector={'N': 1}, treeHash={'b': files.hashBytes(b'')}))
    Traceback (most recent call last):
    Exception: refusing to sync: A and B have diverged
    """
    def raiseDiverged():
        raise Exception('refusing to sync: {} and {} have diverged'.format(
            inA.replicaID, inB.replicaID))

    if inA.treeHash == inB.treeHash:
        return SyncResult(
                versionvector.join(inA.versionVector, inB.versionVector),
                inA.treeHash,
                inA.replicaRoot)
    if inA.versionVector == inB.versionVector:
        return raiseDiverged()
    if versionvector.leq(inA.versionVector, inB.versionVector):
        return SyncResult(inB.versionVector, inB.treeHash, inB.replicaRoot)
    if versionvector.leq(inB.versionVector, inA.versionVector):
        return SyncResult(inA.versionVector, inA.treeHash, inA.replicaRoot)
    return raiseDiverged()


def syncTree(syncResult, syncInput):
    """
    Confirms then overwrites syncInput's tree with syncResult.
    """
    treeChange = files.getTreeChange(syncInput.treeHash, syncResult.treeHash)
    if not files.confirmTreeChange(treeChange, syncInput.replicaID):
        raise Exception('canceled')
    files.applyTreeChange(treeChange,
            src=syncResult.treeRoot, dest=syncInput.replicaRoot)


def sync(otherPath):
    """
    Synchronize the replica in the current directory with the one at otherPath.
    """
    pathA, pathB = '.', otherPath
    syncInputA, syncInputB = map(getSyncInput, [pathA, pathB])
    syncResult = getSyncResult(syncInputA, syncInputB)

    # Sync trees (which confirms all actions) before overwriting the metadata.
    for syncInput in (syncInputA, syncInputB):
        syncTree(syncResult=syncResult, syncInput=syncInput)

    for syncInput in (syncInputA, syncInputB):
        files.setMetaData(files.MetaData(syncInput.replicaID,
            syncResult.versionVector, syncResult.treeHash),
            syncInput.replicaRoot, overwrite=True)

    print('{} and {} synchronized'.format(
        syncInputA.replicaID, syncInputB.replicaID))
