import os
import shutil
import json
import xxhash


def compute_hash(file_path: str) -> str:
    """Compute xxhash64 hash of a file."""
    hasher = xxhash.xxh64()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_hash_list(hash_file: str) -> set:
    """Load existing hashes from file."""
    if os.path.exists(hash_file):
        with open(hash_file, "r") as f:
            return set(json.load(f))
    return set()


def save_hash_list(hash_file: str, hashes: set):
    """Save hashes to file."""
    with open(hash_file, "w") as f:
        json.dump(list(hashes), f, indent=2)


def copy_new_files(source_dir: str, dest_dir: str, hash_file: str):
    """
    Recursively find files in source_dir, copy new ones to dest_dir.

    Files are considered new if their hash is not in the stored hash list.
    The hash list is saved every 50 files and at the end.
    """
    known_hashes = load_hash_list(hash_file)
    os.makedirs(dest_dir, exist_ok=True)

    files_copied = 0
    files_since_save = 0

    for root, _, files in os.walk(source_dir):
        for filename in files:
            file_path = os.path.join(root, filename)

            try:
                file_hash = compute_hash(file_path)
            except (IOError, OSError) as e:
                print(f"Error reading {file_path}: {e}")
                continue

            if file_hash not in known_hashes:
                dest_path = os.path.join(dest_dir, filename)

                # Handle duplicate filenames by adding a suffix
                if os.path.exists(dest_path):
                    base, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(dest_path):
                        dest_path = os.path.join(dest_dir, f"{base}_{counter}{ext}")
                        counter += 1

                try:
                    shutil.copy2(file_path, dest_path)
                    known_hashes.add(file_hash)
                    files_copied += 1
                    files_since_save += 1
                    print(f"Copied: {file_path} -> {dest_path}")

                    # Save every 50 files
                    if files_since_save >= 50:
                        save_hash_list(hash_file, known_hashes)
                        print(f"Saved hash list ({files_copied} files copied so far)")
                        files_since_save = 0

                except (IOError, OSError) as e:
                    print(f"Error copying {file_path}: {e}")

    # Final save
    save_hash_list(hash_file, known_hashes)
    print(f"Complete. {files_copied} new files copied.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Copy new files based on hash comparison")
    parser.add_argument("source", help="Source directory to scan")
    parser.add_argument("dest", help="Destination directory for new files")
    parser.add_argument("--hash-file", default="known_hashes.json",
                        help="File to store known hashes (default: known_hashes.json)")

    args = parser.parse_args()
    copy_new_files(args.source, args.dest, args.hash_file)
