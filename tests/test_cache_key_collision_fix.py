"""
Unit tests for the simplified FastJSONEncoder caching behavior.
"""

from velithon._utils import FastJSONEncoder


class TestFastJSONEncoderSimplified:
    """Test the simplified JSON encoder caching behavior."""

    def setup_method(self):
        """Set up test fixtures."""
        self.encoder = FastJSONEncoder()

    def test_string_caching_only(self):
        """Test that only small strings are cached."""
        # Small strings should be cached
        small_string = "test"
        result1 = self.encoder.encode(small_string)
        result2 = self.encoder.encode(small_string)

        assert result1 == result2
        # Check that cache contains the string
        assert small_string in self.encoder._simple_cache

    def test_no_dictionary_caching(self):
        """Test that dictionaries are not cached (avoiding collision issues)."""
        test_dict = {'name': 'test', 'value': '123'}

        # Encode multiple times
        result1 = self.encoder.encode(test_dict)
        result2 = self.encoder.encode(test_dict)

        # Results should be the same but no caching should occur
        assert result1 == result2
        # Cache should remain empty since we don't cache complex objects
        assert len(self.encoder._simple_cache) == 0

    def test_large_string_not_cached(self):
        """Test that large strings are not cached."""
        # Create a string larger than cache limit (50 chars)
        large_string = "x" * 100

        self.encoder.encode(large_string)

        # Should not be cached due to size
        assert len(self.encoder._simple_cache) == 0

    def test_encoder_backend(self):
        """Test that encoder uses orjson backend."""
        assert self.encoder._backend == 'orjson'
