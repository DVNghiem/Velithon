from __future__ import annotations

import typing

from velithon._velithon import FormParser as RustFormParser
from velithon._velithon import MultiPartParser as RustMultiPartParser
from velithon.datastructures import FormData, Headers
from velithon.exceptions import MultiPartException


class FormParser:
    """High-performance form parser using Rust implementation.
    
    This parser provides significant performance improvements through
    Rust implementation with automatic object binding from Rust.
    """
    
    def __init__(
        self, 
        headers: Headers, 
        stream: typing.AsyncGenerator[bytes, None],
        max_part_size: int = 1024 * 1024  # 1MB default
    ) -> None:
        """Initialize the form parser with headers and data stream."""
        self.headers = headers
        self.stream = stream
        self.max_part_size = max_part_size

    async def parse(self) -> FormData:
        """Parse form data using Rust implementation."""
        # Collect all data from the stream
        data_chunks = []
        async for chunk in self.stream:
            if chunk:
                data_chunks.append(chunk)
        
        if not data_chunks:
            return FormData([])
        
        # Combine all chunks
        full_data = b''.join(data_chunks)
        
        # Create headers dictionary for Rust parser
        headers_dict = dict(self.headers.items())
        
        # Use Rust parser with max_part_size parameter
        rust_parser = RustFormParser(headers_dict, self.max_part_size)
        rust_form_data = rust_parser.parse_form_urlencoded(full_data)
        
        # Convert Rust FormData to Python FormData
        return FormData(rust_form_data.items)


class MultiPartParser:
    """High-performance multipart parser using Rust implementation.
    
    This parser provides significant performance improvements through
    Rust implementation with automatic object binding from Rust.
    """
    
    spool_max_size = 1024 * 1024  # 1MB
    """The maximum size of the spooled temporary file used to store file data."""
    max_part_size = 1024 * 1024  # 1MB
    """The maximum size of a part in the multipart request."""

    def __init__(
        self,
        headers: Headers,
        stream: typing.AsyncGenerator[bytes, None],
        *,
        max_files: int | float = 1000,
        max_fields: int | float = 1000,
        max_part_size: int = 1024 * 1024,  # 1MB
    ) -> None:
        """Initialize the multipart parser with headers and limits."""
        self.headers = headers
        self.stream = stream
        self.max_files = max_files
        self.max_fields = max_fields
        self.max_part_size = max_part_size

    async def parse(self) -> FormData:
        """Parse multipart data using Rust implementation."""
        # Collect all data from the stream
        data_chunks = []
        async for chunk in self.stream:
            if chunk:
                data_chunks.append(chunk)
        
        if not data_chunks:
            return FormData([])
        
        # Combine all chunks
        full_data = b''.join(data_chunks)
        
        # Create headers dictionary for Rust parser
        headers_dict = dict(self.headers.items())
        
        # Use Rust parser
        rust_parser = RustMultiPartParser(
            headers_dict,
            max_files=int(self.max_files),
            max_fields=int(self.max_fields),
            max_part_size=self.max_part_size
        )
        
        try:
            rust_form_data = rust_parser.parse_multipart(full_data)
            # Convert Rust FormData to Python FormData
            return FormData(rust_form_data.items)
        except Exception as e:
            raise MultiPartException(details={'message': str(e)}) from e
