import yaml


class Config:
    @property
    def config(self) -> dict:
        yaml_file = open("config.yaml", "r")
        return yaml.load(yaml_file, Loader=yaml.FullLoader)
