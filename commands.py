import files


def init_replica(replica_id, path):
    meta_data = {
        'replicaID': replica_id,
        'versionVector': {},
        'hashTree': {},
    }
    files.write_meta_data(meta_data, path, overwrite=False)
    print(f'Initialized empty replica {replica_id}.')


def sync(path_a, path_b):
    raise NotImplementedError()
