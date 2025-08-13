# Copyright 2014-2016 OpenMarket Ltd
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

import json
import logging
import re
from typing import IO, Any, Dict, Optional

from twisted.internet import defer
from twisted.web.http import Request

from synapse.api.errors import Codes, SynapseError
from synapse.http.site import SynapseRequest
from synapse.util.stringutils import parse_and_validate_server_name

logger = logging.getLogger(__name__)

# Media ID regex pattern
MEDIA_ID_REGEX = re.compile(r"[A-Za-z0-9_=-]+")


def parse_media_id(request: SynapseRequest) -> Optional[str]:
    """Parse media ID from request path or query parameters.
    
    Args:
        request: The HTTP request.
        
    Returns:
        The media ID if found and valid, None otherwise.
    """
    try:
        # Try to get from path segments
        path_segments = request.path.decode("utf-8").split("/")
        
        # Look for media ID in various positions
        for segment in reversed(path_segments):
            if segment and MEDIA_ID_REGEX.match(segment):
                return segment
                
        # Try query parameter
        media_id = request.args.get(b"media_id")
        if media_id:
            media_id = media_id[0].decode("utf-8")
            if MEDIA_ID_REGEX.match(media_id):
                return media_id
                
        return None
        
    except Exception as e:
        logger.error("Error parsing media ID: %s", e)
        return None


def respond_404(request: SynapseRequest) -> None:
    """Respond with a 404 Not Found error.
    
    Args:
        request: The HTTP request to respond to.
    """
    request.setResponseCode(404)
    request.setHeader(b"Content-Type", b"application/json")
    request.write(json.dumps({
        "errcode": "M_NOT_FOUND",
        "error": "Not found"
    }).encode("utf-8"))
    request.finish()


def respond_with_json(request: SynapseRequest, code: int, json_object: Dict[str, Any]) -> None:
    """Respond with JSON data.
    
    Args:
        request: The HTTP request to respond to.
        code: The HTTP status code.
        json_object: The JSON object to send.
    """
    request.setResponseCode(code)
    request.setHeader(b"Content-Type", b"application/json")
    request.write(json.dumps(json_object).encode("utf-8"))
    request.finish()


async def respond_with_file(request: SynapseRequest, media_type: str, 
                           file_path: str, file_size: Optional[int] = None) -> None:
    """Respond with a file from disk.
    
    Args:
        request: The HTTP request to respond to.
        media_type: The MIME type of the file.
        file_path: Path to the file on disk.
        file_size: Size of the file in bytes (optional).
    """
    try:
        # Set headers
        request.setHeader(b"Content-Type", media_type.encode("utf-8"))
        
        if file_size is not None:
            request.setHeader(b"Content-Length", str(file_size).encode("utf-8"))
            
        # Read and send file
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(8192)  # 8KB chunks
                if not chunk:
                    break
                request.write(chunk)
                
        request.finish()
        
    except FileNotFoundError:
        logger.error("File not found: %s", file_path)
        respond_404(request)
    except Exception as e:
        logger.error("Error serving file %s: %s", file_path, e)
        request.setResponseCode(500)
        request.finish()


async def respond_with_responder(request: SynapseRequest, responder, 
                                media_type: str, media_length: Optional[int] = None) -> None:
    """Respond with a media responder.
    
    Args:
        request: The HTTP request to respond to.
        responder: The media responder object.
        media_type: The MIME type of the media.
        media_length: Length of the media in bytes (optional).
    """
    try:
        # Set headers
        request.setHeader(b"Content-Type", media_type.encode("utf-8"))
        
        if media_length is not None:
            request.setHeader(b"Content-Length", str(media_length).encode("utf-8"))
            
        # Use responder to send data
        if hasattr(responder, 'write_to_consumer'):
            await responder.write_to_consumer(request)
        elif hasattr(responder, 'read'):
            # Simple file-like responder
            while True:
                chunk = responder.read(8192)
                if not chunk:
                    break
                request.write(chunk)
        else:
            # Fallback: treat as bytes
            request.write(responder)
            
        request.finish()
        
    except Exception as e:
        logger.error("Error with responder: %s", e)
        respond_404(request)


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
        
    def __str__(self) -> str:
        return (
            f"FileInfo(server_name={self.server_name}, file_id={self.file_id}, "
            f"thumbnail={self.thumbnail})"
        )


class Responder:
    """Base class for media responders."""
    
    def __init__(self, file_like: IO):
        self.file_like = file_like
        
    def read(self, size: int = -1) -> bytes:
        """Read data from the responder.
        
        Args:
            size: Number of bytes to read. -1 means read all.
            
        Returns:
            The data read.
        """
        return self.file_like.read(size)
        
    async def write_to_consumer(self, consumer) -> None:
        """Write data to a consumer.
        
        Args:
            consumer: The consumer to write to.
        """
        try:
            while True:
                chunk = self.read(8192)
                if not chunk:
                    break
                consumer.write(chunk)
        finally:
            self.close()
            
    def close(self) -> None:
        """Close the responder."""
        if hasattr(self.file_like, 'close'):
            self.file_like.close()
            
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class FileResponder(Responder):
    """Responder for files on disk."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._file = None
        
    def read(self, size: int = -1) -> bytes:
        """Read data from the file."""
        if self._file is None:
            self._file = open(self.file_path, "rb")
        return self._file.read(size)
        
    def close(self) -> None:
        """Close the file."""
        if self._file is not None:
            self._file.close()
            self._file = None


def validate_server_name(server_name: str) -> str:
    """Validate and normalize a server name.
    
    Args:
        server_name: The server name to validate.
        
    Returns:
        The validated server name.
        
    Raises:
        SynapseError: If the server name is invalid.
    """
    try:
        return parse_and_validate_server_name(server_name)
    except ValueError as e:
        raise SynapseError(
            400, f"Invalid server name: {e}", Codes.INVALID_PARAM
        )


def get_filename_from_headers(headers: Dict[bytes, bytes]) -> Optional[str]:
    """Extract filename from HTTP headers.
    
    Args:
        headers: The HTTP headers.
        
    Returns:
        The filename if found, None otherwise.
    """
    content_disposition = headers.get(b"content-disposition")
    if not content_disposition:
        return None
        
    try:
        # Simple parsing of Content-Disposition header
        disposition = content_disposition.decode("utf-8")
        if "filename=" in disposition:
            # Extract filename (basic implementation)
            parts = disposition.split("filename=")
            if len(parts) > 1:
                filename = parts[1].strip('"\'')
                return filename
    except Exception as e:
        logger.error("Error parsing Content-Disposition header: %s", e)
        
    return None