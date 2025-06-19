"""
Unit tests for cache key collision prevention in FastJSONEncoder.
"""

import pytest

from velithon._utils import FastJSONEncoder


class TestFastJSONEncoderCacheKeys:
    """Test cache key generation for collision prevention."""

    def setup_method(self):
        """Set up test fixtures."""
        self.encoder = FastJSONEncoder()

    def test_cache_key_collision_prevention(self):
        """Test that cache keys prevent collisions for tricky cases."""
        # Test cases that would create collisions with naive approaches
        collision_cases = [
            # Separator character conflicts
            ({'a:b': 'c'}, {'a': 'b:c'}),
            ({'a|b': 'c'}, {'a': 'b|c'}),
            ({'a:b|c': 'd'}, {'a': 'b:c|d'}),
            # Empty keys/values
            ({'': 'a:b'}, {'a': ':b'}),
            ({'key': ''}, {':key': ''}),
            # Backslash escaping
            ({'a': 'b\\c'}, {'a\\': 'bc'}),
            ({'a\\b': 'c'}, {'a': 'b\\c'}),
            # Complex mixed cases
            ({'key': 'val:ue'}, {'ke:y': 'value'}),
            ({'a:b\\c': 'd|e'}, {'a': 'b:c\\d|e'}),
        ]

        for dict1, dict2 in collision_cases:
            key1 = self.encoder._create_dict_cache_key(dict1)
            key2 = self.encoder._create_dict_cache_key(dict2)

            assert key1 != key2, (
                f'Collision detected between {dict1} and {dict2}. '
                f'Both generated key: {key1}'
            )

    def test_cache_key_consistency(self):
        """Test that identical dicts produce identical cache keys."""
        test_dict = {'name': 'test', 'value': '123', 'flag': 'true'}

        key1 = self.encoder._create_dict_cache_key(test_dict)
        key2 = self.encoder._create_dict_cache_key(test_dict)

        assert key1 == key2, (
            'Identical dictionaries should produce identical cache keys'
        )

    def test_cache_key_order_independence(self):
        """Test that key order doesn't affect cache key generation."""
        dict1 = {'b': '2', 'a': '1', 'c': '3'}
        dict2 = {'a': '1', 'b': '2', 'c': '3'}
        dict3 = {'c': '3', 'a': '1', 'b': '2'}

        key1 = self.encoder._create_dict_cache_key(dict1)
        key2 = self.encoder._create_dict_cache_key(dict2)
        key3 = self.encoder._create_dict_cache_key(dict3)

        assert key1 == key2 == key3, (
            'Dictionary key order should not affect cache key generation'
        )

    def test_cache_key_format_validation(self):
        """Test that cache keys follow expected format."""
        test_dict = {'key': 'value'}
        cache_key = self.encoder._create_dict_cache_key(test_dict)

        # Should contain length prefixes and proper separators
        assert '3:key=5:value' in cache_key

        # Test with special characters
        special_dict = {'a:b': 'c|d'}
        special_key = self.encoder._create_dict_cache_key(special_dict)

        # Should properly escape special characters
        assert '4:a\\:b=4:c\\|d' in special_key

    def test_cache_key_edge_cases(self):
        """Test edge cases for cache key generation."""
        edge_cases = [
            {},  # Empty dict
            {'': ''},  # Empty key and value
            {'key': ''},  # Empty value
            {'': 'value'},  # Empty key
            {'a' * 100: 'b' * 100},  # Long strings
            {'unicode': '测试🚀'},  # Unicode characters
        ]

        for test_dict in edge_cases:
            try:
                cache_key = self.encoder._create_dict_cache_key(test_dict)
                assert isinstance(cache_key, str), (
                    f'Cache key should be string for {test_dict}'
                )
                assert len(cache_key) >= 0, (
                    f'Cache key should not be negative length for {test_dict}'
                )
            except Exception as e:
                pytest.fail(f'Cache key generation failed for {test_dict}: {e}')

    def test_encode_with_dict_caching(self):
        """Test that the encode method properly uses dict caching."""
        # Small dict should use caching
        small_dict = {'a': '1', 'b': '2'}

        # First call should cache
        result1 = self.encoder.encode(small_dict)

        # Second call should hit cache
        result2 = self.encoder.encode(small_dict)

        assert result1 == result2
        assert isinstance(result1, bytes)
        assert isinstance(result2, bytes)

        # Verify JSON content is correct
        import json

        decoded = json.loads(result1.decode('utf-8'))
        assert decoded == small_dict

    def test_encode_large_dict_no_caching(self):
        """Test that large dicts don't use caching."""
        # Dict with more than 5 keys should not use caching
        large_dict = {f'key{i}': f'value{i}' for i in range(10)}

        # Should still encode correctly
        result = self.encoder.encode(large_dict)
        assert isinstance(result, bytes)

        # Verify JSON content is correct
        import json

        decoded = json.loads(result.decode('utf-8'))
        assert decoded == large_dict
