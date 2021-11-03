from collections.abc import Mapping
from collections.abc import MutableMapping


class MappingMixin(Mapping):
    def __init__(self):
        self.mapping: dict = {}

    def __getitem__(self, key):
        return self.mapping[key]

    def __iter__(self):
        return iter(self.mapping)

    def __len__(self):
        return len(self.mapping)

    def __repr__(self):
        return f"{type(self).__name__}({self.mapping})"


class MutableMappingMixin(MutableMapping):
    def __init__(self):
        self.mapping: dict = {}

    def __getitem__(self, key):
        return self.mapping[key]

    def __delitem__(self, key):
        value = self[key]
        del self.mapping[key]
        self.pop(value, None)

    def __setitem__(self, key, value):
        if key in self:
            del self[self[key]]

        if value in self:
            del self[value]

        self.mapping[key] = value
        self.mapping[value] = key

    def __iter__(self):
        return iter(self.mapping)

    def __len__(self):
        return len(self.mapping)

    def __repr__(self):
        return f"{type(self).__name__}({self.mapping})"
