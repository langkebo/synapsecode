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

"""Matrix media repository v1 API."""

from .download_resource import DownloadResource
from .media_repository import MediaRepositoryResource
from .media_storage import MediaStorage, FileInfo
from .thumbnail_resource import ThumbnailResource
from .upload_resource import UploadResource

__all__ = [
    "DownloadResource",
    "MediaRepositoryResource", 
    "MediaStorage",
    "FileInfo",
    "ThumbnailResource",
    "UploadResource",
]