"""Feature mapping for all input and output features."""

import itertools
from typing import Dict, TYPE_CHECKING
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Mapping
from typing import Optional
from typing import Union

from unipi_control.config import LogPrefix
from unipi_control.features.extensions import EastronMeter
from unipi_control.features.neuron import DigitalInput
from unipi_control.features.neuron import DigitalOutput
from unipi_control.features.neuron import Led
from unipi_control.features.neuron import Relay
from unipi_control.helpers.exception import ConfigError

if TYPE_CHECKING:
    from unipi_control.features.utils import FeatureType


class FeatureMap(Mapping[str, List[Union[DigitalInput, DigitalOutput, Led, Relay, EastronMeter]]]):
    def __init__(self) -> None:
        self.data: Dict[str, List[Union[DigitalInput, DigitalOutput, Led, Relay, EastronMeter]]] = {}

    def __getitem__(self, key: str) -> List[Union[DigitalInput, DigitalOutput, Led, Relay, EastronMeter]]:
        data: List[Union[DigitalInput, DigitalOutput, Led, Relay, EastronMeter]] = self.data[key]
        return data

    def __iter__(self) -> Iterator[str]:
        return iter(self.data)

    def __len__(self) -> int:
        _length: int = 0

        for data in self.data.values():
            _length += len(data)

        return _length

    def register(self, feature: Union[DigitalInput, DigitalOutput, Led, Relay, EastronMeter]) -> None:
        """Add a feature to the data storage.

        Parameters
        ----------
        feature: Feature
            Input or output feature.
        """
        feature_type: FeatureType = feature.hardware.feature_type

        if not self.get(feature_type.short_name):
            self.data[feature_type.short_name] = []

        self.data[feature_type.short_name].append(feature)

    def by_feature_id(
        self, feature_id: str, feature_types: Optional[List[str]] = None
    ) -> Union[DigitalInput, DigitalOutput, Led, Relay, EastronMeter]:
        """Get feature by object id.

        Parameters
        ----------
        feature_id: str
            The machine-readable unique name e.g. ro_2_01.
        feature_types: list, optional
            List of feature types e.g. DI, RO, ...

        Returns
        -------
        The feature class filtered by circuit.

        Raises
        ------
        ConfigError
            Get an exception if feature type not found.
        """
        data: Iterable[Union[DigitalInput, DigitalOutput, Led, Relay, EastronMeter]] = itertools.chain.from_iterable(
            self.values()
        )

        if feature_types:
            data = self.by_feature_types(feature_types)

        try:
            features: Union[DigitalInput, DigitalOutput, Led, Relay, EastronMeter] = next(
                d for d in data if d.feature_id == feature_id
            )
        except StopIteration as error:
            msg = f"{LogPrefix.CONFIG} '{feature_id}' not found in {self.__class__.__name__}!"
            raise ConfigError(msg) from error

        return features

    def by_feature_types(
        self, feature_types: List[str]
    ) -> Iterator[Union[DigitalInput, DigitalOutput, Led, Relay, EastronMeter]]:
        """Filter features by feature type.

        Parameters
        ----------
        feature_types: list
            List of feature types e.g. DI, RO, ...

        Returns
        -------
        Iterator
            A list of features filtered by feature type.
        """
        return itertools.chain.from_iterable(
            [item for item in (self.get(feature_type) for feature_type in feature_types) if item is not None]
        )
