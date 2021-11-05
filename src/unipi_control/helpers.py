from collections.abc import MutableMapping


class MutableMappingMixin(MutableMapping):
    """A custom read-only mutable mappings class.

    Attributes
    ----------
    mapping: dict

    """
    def __init__(self):
        self.mapping: dict = {}

    def __getitem__(self, key):
        return self.mapping[key]

    def __setitem__(self, key, value):
        self.mapping[key] = value

    def __iter__(self):
        return iter(self.mapping)

    def __len__(self):
        return len(self.mapping)

    def __repr__(self):
        return f"{type(self).__name__}({self.mapping})"
