"""Feature mapping for all input and output features."""

import itertools
from typing import Dict
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Mapping
from typing import Optional
from typing import Union

from unipi_control.config import LogPrefix
from unipi_control.features.eastron import Eastron
from unipi_control.features.constants import FeatureType
from unipi_control.features.unipi import DigitalInput
from unipi_control.features.unipi import DigitalOutput
from unipi_control.features.unipi import Led
from unipi_control.features.unipi import Relay
from unipi_control.helpers.exceptions import ConfigError


class FeatureMap(Mapping[str, List[Union[DigitalInput, DigitalOutput, Led, Relay, Eastron]]]):
    def __init__(self) -> None:
        self.data: Dict[str, List[Union[DigitalInput, DigitalOutput, Led, Relay, Eastron]]] = {}

    def __getitem__(self, key: str) -> List[Union[DigitalInput, DigitalOutput, Led, Relay, Eastron]]:
        data: List[Union[DigitalInput, DigitalOutput, Led, Relay, Eastron]] = self.data[key]
        return data

    def __iter__(self) -> Iterator[str]:
        return iter(self.data)

    def __len__(self) -> int:
        _length: int = 0

        for data in self.data.values():
            _length += len(data)

        return _length

    def register(self, feature: Union[DigitalInput, DigitalOutput, Led, Relay, Eastron]) -> None:
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
        self, feature_id: str, feature_types: Optional[List[FeatureType]] = None
    ) -> Union[DigitalInput, DigitalOutput, Led, Relay, Eastron]:
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
        data: Iterable[Union[DigitalInput, DigitalOutput, Led, Relay, Eastron]] = itertools.chain.from_iterable(
            self.values()
        )

        if feature_types:
            data = self.by_feature_types(feature_types)

        try:
            features: Union[DigitalInput, DigitalOutput, Led, Relay, Eastron] = next(
                d for d in data if d.feature_id == feature_id
            )
        except StopIteration as error:
            msg = f"{LogPrefix.CONFIG} '{feature_id}' not found in {self.__class__.__name__}!"
            raise ConfigError(msg) from error

        return features

    def by_feature_types(
        self, feature_types: List[FeatureType]
    ) -> Iterator[Union[DigitalInput, DigitalOutput, Led, Relay, Eastron]]:
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
            [item for item in (self.get(feature_type.name) for feature_type in feature_types) if item is not None]
        )
