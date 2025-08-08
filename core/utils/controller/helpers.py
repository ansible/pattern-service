import contextlib
import logging
import os
import shutil
import tarfile
import tempfile
from typing import Iterator
from urllib.parse import urljoin

from django.conf import settings

from .client import get

logger = logging.getLogger(__name__)


def build_collection_uri(collection: str, version: str) -> str:
    """
    Builds the full URI for a given collection and version.

    Args:
        collection (str): The collection name.
        version (str): The version string.

    Returns:
        str: The full URI to the collection artifact.
    """
    path = "/api/galaxy/v3/plugin/ansible/content/published/collections/artifacts"
    filename = f"{collection}-{version}.tar.gz"

    return urljoin(f"{settings.AAP_URL}/", f"{path}/{filename}")


@contextlib.contextmanager
def download_collection(collection_name: str, version: str) -> Iterator[str]:
    """
    Downloads and extracts a collection tarball from private automation hub to a
    temporary directory.

    Args:
        collection_name: The name of the collection (e.g., 'my_namespace.my_collection').
        version: The version of the collection (e.g., '1.0.0').

    Yields:
        The path to the extracted collection files.
    """
    response = None
    collection = collection_name.replace(".", "-")
    temp_base_dir = tempfile.mkdtemp()
    collection_path = os.path.join(temp_base_dir, f"{collection}-{version}")
    os.makedirs(collection_path, exist_ok=True)
    path = build_collection_uri(collection, version)

    try:
        response = get(path)

        with tarfile.open(fileobj=response.raw, mode="r|gz") as tar:
            tar.extractall(path=collection_path, filter="data")

        logger.info(f"Collection extracted to {collection_path}")
        yield collection_path  # Yield the path to the caller
    finally:
        shutil.rmtree(temp_base_dir)
