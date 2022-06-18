import hashlib
import os
import shutil
from pathlib import Path

BLOCKSIZE = 65536


def hash_file(path):
    hasher = hashlib.sha1()
    with path.open("rb") as file:
        buf = file.read(BLOCKSIZE)
        while buf:
            hasher.update(buf)
            buf = file.read(BLOCKSIZE)
    return hasher.hexdigest()


def read_paths_and_hashes(root):
    hashes = {}
    for folder, _, files in os.walk(root):
        for fn in files:
            hashes[hash_file(Path(folder) / fn)] = fn
    return hashes


def determine_actions(src_hashes, dst_hashes, src_folder, dst_folder):
    for sha, filename in src_hashes.items():
        if sha not in dst_hashes:
            source_path = Path(src_folder) / filename
            dest_path = Path(dst_folder) / filename
            yield "copy", source_path, dest_path
        elif dst_hashes[sha] != filename:
            old_dest_path = Path(dst_folder) / dst_hashes[sha]
            new_dest_path = Path(dst_folder) / filename
            yield "move", old_dest_path, new_dest_path

    for sha, filename in dst_hashes.items():
        if sha not in src_hashes:
            yield "delete", dst_folder / filename


def sync(source, dest):

    source_hashes = read_paths_and_hashes(source)
    dest_hashes = read_paths_and_hashes(dest)

    actions = determine_actions(source_hashes, dest_hashes, source, dest)

    for action, *paths in actions:
        if action == "copy":
            shutil.copyfile(*paths)
        if action == "move":
            shutil.move(*paths)

        if action == "delete":
            os.remove(paths[0])
