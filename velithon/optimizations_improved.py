#!/usr/bin/env python3
"""
A simplified object pool implementation without thread safety overhead for 
situations where the performance impact of thread safety isn't justified.
"""

class SimpleObjectPool:
    """A simplified object pool without thread safety overhead."""
    
    def __init__(self, factory, max_size=100):
        self.factory = factory
        self.max_size = max_size
        self.pool = []
    
    def get(self):
        """Get an object from the pool or create a new one."""
        if self.pool:
            return self.pool.pop()
        return self.factory()

    def put(self, obj):
        """Return an object to the pool."""
        if len(self.pool) < self.max_size:
            # Reset object state if it has a reset method
            if hasattr(obj, "reset"):
                obj.reset()
            self.pool.append(obj)


# Example implementation to replace Velithon's object pools
_simple_dict_pool = SimpleObjectPool(dict, max_size=200)
_simple_list_pool = SimpleObjectPool(list, max_size=200)

def get_dict_from_simple_pool():
    """Get a dictionary from the simplified object pool."""
    return _simple_dict_pool.get()

def return_dict_to_simple_pool(d):
    """Return a dictionary to the simplified object pool."""
    d.clear()
    _simple_dict_pool.put(d)

def get_list_from_simple_pool():
    """Get a list from the simplified object pool."""
    return _simple_list_pool.get()

def return_list_to_simple_pool(lst):
    """Return a list to the simplified object pool."""
    lst.clear()
    _simple_list_pool.put(lst)
