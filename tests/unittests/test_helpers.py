from unipi_control.helpers import DataStorage


class TestHappyPathHelpers:
    def test_data_storage(self):
        data_storage: DataStorage = DataStorage()

        data_storage["key"] = "value"

        assert "value" == data_storage["key"]
        assert 1 == len(data_storage)
        assert ["key"] == [d for d in data_storage]
        assert "DataStorage({'key': 'value'})" == str(data_storage)

        del data_storage["key"]

        assert 0 == len(data_storage)
