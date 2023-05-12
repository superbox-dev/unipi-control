import itertools
from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional
from typing import Union

from unipi_control.config import LogPrefix
from unipi_control.exception import ConfigError
from unipi_control.features.extensions import EastronMeter
from unipi_control.features.neuron import DigitalInput
from unipi_control.features.neuron import DigitalOutput
from unipi_control.features.neuron import Led
from unipi_control.features.neuron import Relay
from unipi_control.features.utils import FeatureType


class FeatureMap:
    def __init__(self) -> None:
        self.data: Dict[str, List[Union[DigitalInput, DigitalOutput, Led, Relay, EastronMeter]]] = {}

    def register(self, feature: Union[DigitalInput, DigitalOutput, Led, Relay, EastronMeter]) -> None:
        """Add a feature to the data storage.

        Parameters
        ----------
        feature: Feature
        """
        feature_type: FeatureType = feature.hardware.feature_type

        if not self.data.get(feature_type.short_name):
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
        feature_types: list

        Returns
        -------
        The feature class filtered by circuit.

        Raises
        ------
        ConfigException
            Get an exception if feature type not found.
        """
        data: Iterator = itertools.chain.from_iterable(self.data.values())

        if feature_types:
            data = self.by_feature_types(feature_types)

        try:
            feature: Union[DigitalInput, DigitalOutput, Led, Relay, EastronMeter] = next(
                d for d in data if d.feature_id == feature_id
            )
        except StopIteration as error:
            msg = f"{LogPrefix.CONFIG} '{feature_id}' not found in {self.__class__.__name__}!"
            raise ConfigError(msg) from error

        return feature

    def by_feature_types(self, feature_types: List[str]) -> Iterator:
        """Filter features by feature type.

        Parameters
        ----------
        feature_types: list

        Returns
        -------
        Iterator
            A list of features filtered by feature type.
        """
        return itertools.chain.from_iterable(
            [item for item in (self.data.get(feature_type) for feature_type in feature_types) if item is not None]
        )
