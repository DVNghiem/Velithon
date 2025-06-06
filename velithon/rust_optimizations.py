"""
Enhanced performance utilities using Rust optimizations
"""

from typing import Dict, Any, List, Tuple, Optional, Union
import json
from velithon import _velithon

class FastJSONEncoder:
    """Fast JSON encoder using Rust implementation with caching"""
    
    def __init__(self, max_cache_size: int = 1000):
        self._encoder = _velithon.RustJSONEncoder(max_cache_size=max_cache_size)
    
    def encode(self, obj: Any) -> bytes:
        """Encode Python object to JSON bytes"""
        return self._encoder.encode(obj)
    
    def encode_str(self, obj: Any) -> str:
        """Encode Python object to JSON string"""
        return self.encode(obj).decode('utf-8')
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        hits, misses, hit_rate = self._encoder.get_cache_stats()
        return {
            "cache_hits": hits,
            "cache_misses": misses,
            "hit_rate": hit_rate,
            "total_requests": hits + misses
        }
    
    def clear_cache(self) -> None:
        """Clear the encoding cache"""
        self._encoder.clear_cache()

class FastRouteCache:
    """Fast route matching and caching using Rust implementation"""
    
    def __init__(self, max_cache_size: int = 10000):
        self._cache = _velithon.RouteCache(max_cache_size=max_cache_size)
    
    def add_route(self, pattern: str, regex_str: str, param_names: List[str], 
                  methods: Optional[List[str]] = None) -> None:
        """Add a route pattern to the cache"""
        self._cache.add_route(pattern, regex_str, param_names, methods)
    
    def match_route(self, path: str, method: str) -> Tuple[str, Dict[str, str]]:
        """Match a path against registered routes"""
        return self._cache.match_route(path, method)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        hits, misses, hit_rate, entries = self._cache.get_cache_stats()
        return {
            "cache_hits": hits,
            "cache_misses": misses,
            "hit_rate": hit_rate,
            "cache_entries": entries
        }
    
    def clear_cache(self) -> None:
        """Clear the route matching cache"""
        self._cache.clear_cache()

class FastParameterParser:
    """Fast query string and form parameter parsing using Rust implementation"""
    
    def __init__(self, max_cache_size: int = 500):
        self._parser = _velithon.ParameterParser(max_cache_size=max_cache_size)
    
    def parse_query_string(self, query_string: str) -> Dict[str, str]:
        """Parse a query string into a dictionary"""
        return self._parser.parse_query_string(query_string)
    
    def parse_form_data(self, form_data: str) -> Dict[str, str]:
        """Parse form data into a dictionary"""
        return self._parser.parse_form_data(form_data)
    
    def get_cache_size(self) -> int:
        """Get current cache size"""
        return self._parser.get_cache_size()
    
    def clear_cache(self) -> None:
        """Clear the parameter parsing cache"""
        self._parser.clear_cache()

class FastHeaderProcessor:
    """Fast HTTP header processing using Rust implementation"""
    
    def __init__(self, max_cache_size: int = 500):
        self._processor = _velithon.HeaderProcessor(max_cache_size=max_cache_size)
    
    def parse_headers(self, headers: List[Tuple[str, str]]) -> Dict[str, Union[str, List[str]]]:
        """Parse HTTP headers into a normalized dictionary"""
        return self._processor.parse_headers(headers)
    
    def parse_content_type(self, content_type: str) -> Tuple[str, Dict[str, str]]:
        """Parse Content-Type header into media type and parameters"""
        return self._processor.parse_content_type(content_type)
    
    def validate_headers(self, headers: Dict[str, str]) -> List[str]:
        """Validate headers and return list of errors"""
        return self._processor.validate_headers(headers)
    
    def optimize_response_headers(self, headers: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """Optimize headers for response (remove duplicates, normalize)"""
        return self._processor.optimize_response_headers(headers)
    
    def clear_caches(self) -> None:
        """Clear all header processing caches"""
        self._processor.clear_caches()

class FastCookieProcessor:
    """Fast cookie parsing using Rust implementation"""
    
    def __init__(self, max_cache_size: int = 500):
        self._processor = _velithon.CookieProcessor(max_cache_size=max_cache_size)
    
    def parse_cookies(self, cookie_header: str) -> Dict[str, str]:
        """Parse cookie header into a dictionary"""
        return self._processor.parse_cookies(cookie_header)
    
    def clear_cache(self) -> None:
        """Clear the cookie parsing cache"""
        self._processor.clear_cache()

# Global instances for framework use
_json_encoder = None
_route_cache = None
_parameter_parser = None
_header_processor = None
_cookie_processor = None

def get_json_encoder() -> FastJSONEncoder:
    """Get global JSON encoder instance"""
    global _json_encoder
    if _json_encoder is None:
        _json_encoder = FastJSONEncoder()
    return _json_encoder

def get_route_cache() -> FastRouteCache:
    """Get global route cache instance"""
    global _route_cache
    if _route_cache is None:
        _route_cache = FastRouteCache()
    return _route_cache

def get_parameter_parser() -> FastParameterParser:
    """Get global parameter parser instance"""
    global _parameter_parser
    if _parameter_parser is None:
        _parameter_parser = FastParameterParser()
    return _parameter_parser

def get_header_processor() -> FastHeaderProcessor:
    """Get global header processor instance"""
    global _header_processor
    if _header_processor is None:
        _header_processor = FastHeaderProcessor()
    return _header_processor

def get_cookie_processor() -> FastCookieProcessor:
    """Get global cookie processor instance"""
    global _cookie_processor
    if _cookie_processor is None:
        _cookie_processor = FastCookieProcessor()
    return _cookie_processor

def clear_all_caches():
    """Clear all optimization caches"""
    global _json_encoder, _route_cache, _parameter_parser, _header_processor, _cookie_processor
    
    if _json_encoder:
        _json_encoder.clear_cache()
    if _route_cache:
        _route_cache.clear_cache()
    if _parameter_parser:
        _parameter_parser.clear_cache()
    if _header_processor:
        _header_processor.clear_caches()
    if _cookie_processor:
        _cookie_processor.clear_cache()

def get_all_stats() -> Dict[str, Any]:
    """Get performance statistics from all optimizations"""
    stats = {}
    
    if _json_encoder:
        stats['json_encoder'] = _json_encoder.get_stats()
    if _route_cache:
        stats['route_cache'] = _route_cache.get_stats()
    if _parameter_parser:
        stats['parameter_parser'] = {'cache_size': _parameter_parser.get_cache_size()}
    
    return stats
