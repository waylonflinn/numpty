"""Text and binary file functions."""

from pathlib import Path


def read_file(path: str, encoding: str = "utf-8"):
    """Read a text file.

    Args:
        path: File path.
        encoding: Text encoding.

    Returns:
        File contents.
    """
    file_path = Path(path)
    return file_path.read_text(encoding=encoding)


def read_binary(path:str):
    """Read a file as bytes.
      Not meant for direct use as a model tool: output is raw bytes.

    Args:
        path: File path.

    Returns:
        File contents.
    """
    file_path = Path(path)
    return file_path.read_bytes()


def write_file(path: str, content: str, encoding: str = "utf-8"):
    """Write text to a file. Replaces existing contents. Makes the file if missing.

    Args:
        path: File path. Parent directory must exist.
        content: Text to write.
        encoding: Text encoding.

    Returns:
        Number of characters written.
    """
    file_path = Path(path)
    return file_path.write_text(content, encoding=encoding)


def append_file(path: str, content: str, encoding: str = "utf-8"):
    """Add text to the end of a file. Makes the file if missing.

    Args:
        path: File path. Parent directory must exist.
        content: Text to add.
        encoding: Text encoding.

    Returns:
        Number of characters written.
    """
    file_path = Path(path)
    with file_path.open(mode="a", encoding=encoding) as file:
        return file.write(content)
