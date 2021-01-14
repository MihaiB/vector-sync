import file_ops


def init(args):
    file_ops.init_file_tree(treepath='.', tree_id=args.id)


def sync(args):
    raise NotImplementedError()
