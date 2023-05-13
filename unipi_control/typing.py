from typing import Any
from typing import ClassVar
from typing import Dict
from typing import Protocol
from typing import TypeVar

_T = TypeVar("_T")
_R = TypeVar("_R")


class DataClassProtocol(Protocol):
    __dataclass_fields__: ClassVar[Dict[str, Any]]
