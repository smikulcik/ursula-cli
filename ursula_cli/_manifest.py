import yaml


class Manifest(object):
    def __init__(self, data):
        self.ansible_version = data['ansible']['version']

    @staticmethod
    def load_file(path):
        dct = yaml.safe_load(file(path, 'r'))
        return Manifest(dct)
