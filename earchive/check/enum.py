from enum import EnumType, StrEnum, _EnumDict


class nested(str): ...


class NestedEnumType(EnumType):
    def __new__(metacls, cls, bases, classdict: _EnumDict, *, boundary=None, _simple=False, **kwds):
        _gnv = staticmethod(classdict._generate_next_value)  # pyright: ignore[reportAttributeAccessIssue]
        _parents = {}
        _updated_members = {}

        for name in classdict._member_names:  # pyright: ignore[reportAttributeAccessIssue]
            value = classdict[name]
            if isinstance(value, nested):
                if name not in classdict:
                    raise ValueError(f"nested() referenced non-existent member '{value}'")

                _parents[name] = name
                _updated_members[name] = _gnv(name, None, None, None)

        for name in _updated_members:
            del classdict._member_names[name]  # pyright: ignore[reportAttributeAccessIssue]
            del classdict[name]
        classdict.update(_updated_members)

        # delegate member instanciation
        obj = super().__new__(metacls, cls, bases, classdict, boundary=boundary, _simple=_simple, **kwds)

        # update _parents dict with actual member objects
        obj._parents = {name: obj.__members__[value] for name, value in _parents.items()}  # pyright: ignore[reportAttributeAccessIssue]
        return obj


class StrNestedEnum(StrEnum, metaclass=NestedEnumType): ...


class NestedEnumDict[K: StrNestedEnum, V](dict[K, V]):
    def __init__(self, typ: type[StrNestedEnum], dct: dict[K, V]):
        self._typ = typ
        super().__init__(dct)

    def __getitem__(self, key: K, /) -> V:
        try:
            return super().__getitem__(key)
        except KeyError as e:
            parent = self._typ._parents.get(key)  # pyright: ignore[reportAttributeAccessIssue]
            if parent is None:
                raise e

            return self.__getitem__(parent)
