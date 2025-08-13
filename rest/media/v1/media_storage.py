# Copyright 2018-2021 The Matrix.org Foundation C.I.C.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
import shutil
from typing import IO, TYPE_CHECKING, Any, Callable, Optional, Sequence

from twisted.internet import defer
from twisted.internet.defer import Deferred

from synapse.logging.context import defer_to_thread
from synapse.util.file_consumer import BackgroundFileConsumer

if TYPE_CHECKING:
    from synapse.server import HomeServer

logger = logging.getLogger(__name__)


class MediaStorage:
    """Responsible for storing and retrieving media files."""

    def __init__(self, hs: "HomeServer", local_media_directory: str, filepaths):
        self.hs = hs
        self.local_media_directory = local_media_directory
        self.filepaths = filepaths
        self.clock = hs.get_clock()

    def ensure_media_is_in_local_cache(self, file_info) -> Deferred:
        """Ensures that the given file is in the local cache.
        
        Args:
            file_info: The file info for the media.
            
        Returns:
            A Deferred that resolves to the local path of the file.
        """
        local_path = self.filepaths.local_media_filepath(file_info.media_id)
        
        if os.path.exists(local_path):
            return defer.succeed(local_path)
        
        # File doesn't exist locally, need to download or create
        return defer.fail(FileNotFoundError(f"Media file not found: {file_info.media_id}"))

    async def store_file(self, source: IO, file_info) -> str:
        """Store a file from the given source.
        
        Args:
            source: The source file-like object to read from.
            file_info: Information about the file being stored.
            
        Returns:
            The local path where the file was stored.
        """
        fname = self.filepaths.local_media_filepath(file_info.media_id)
        dirname = os.path.dirname(fname)
        
        # Ensure directory exists
        os.makedirs(dirname, exist_ok=True)
        
        # Write file to temporary location first
        temp_fname = fname + ".tmp"
        
        def _write_file():
            with open(temp_fname, "wb") as f:
                shutil.copyfileobj(source, f)
            # Atomically move to final location
            os.rename(temp_fname, fname)
            return fname
        
        return await defer_to_thread(self.hs.get_reactor(), _write_file)

    async def write_to_file(self, source: IO, output_file: IO) -> None:
        """Write from source to output file.
        
        Args:
            source: The source file-like object to read from.
            output_file: The output file-like object to write to.
        """
        def _write():
            shutil.copyfileobj(source, output_file)
        
        await defer_to_thread(self.hs.get_reactor(), _write)

    def file_consumer(self, file_like: IO) -> BackgroundFileConsumer:
        """Create a file consumer for writing to the given file.
        
        Args:
            file_like: The file-like object to write to.
            
        Returns:
            A BackgroundFileConsumer instance.
        """
        return BackgroundFileConsumer(file_like, self.hs.get_reactor())

    async def copy_to_backup_location(self, file_info, source_path: str) -> None:
        """Copy a file to backup location if configured.
        
        Args:
            file_info: Information about the file.
            source_path: The source file path.
        """
        # This is a placeholder for backup functionality
        # In a real implementation, this would copy to backup storage
        logger.debug("Backup copy requested for %s", file_info.media_id)

    async def move_from_backup_location(self, file_info) -> str:
        """Move a file from backup location to local cache.
        
        Args:
            file_info: Information about the file.
            
        Returns:
            The local path where the file was moved.
        """
        # This is a placeholder for backup restore functionality
        local_path = self.filepaths.local_media_filepath(file_info.media_id)
        
        if os.path.exists(local_path):
            return local_path
        
        raise FileNotFoundError(f"Cannot restore from backup: {file_info.media_id}")


class ReadableFileWrapper:
    """Wrapper for readable file objects."""
    
    def __init__(self, file_like: IO):
        self.file_like = file_like
        
    def read(self, size: int = -1) -> bytes:
        """Read data from the file.
        
        Args:
            size: Number of bytes to read. -1 means read all.
            
        Returns:
            The data read from the file.
        """
        return self.file_like.read(size)
        
    def close(self) -> None:
        """Close the file."""
        self.file_like.close()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class FileInfo:
    """Information about a file being stored or retrieved."""
    
    def __init__(self, server_name: Optional[str], file_id: str, 
                 url_cache: bool = False, thumbnail: bool = False,
                 thumbnail_width: Optional[int] = None,
                 thumbnail_height: Optional[int] = None,
                 thumbnail_method: Optional[str] = None,
                 thumbnail_type: Optional[str] = None):
        self.server_name = server_name
        self.file_id = file_id
        self.url_cache = url_cache
        self.thumbnail = thumbnail
        self.thumbnail_width = thumbnail_width
        self.thumbnail_height = thumbnail_height
        self.thumbnail_method = thumbnail_method
        self.thumbnail_type = thumbnail_type
        
    @property
    def media_id(self) -> str:
        """Get the media ID for this file."""
        return self.file_id