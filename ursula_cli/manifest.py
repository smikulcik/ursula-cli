import os
import yaml


class UrsulaManifest(object):
    def __init__(self, **kwargs):
        self.ansible_version = kwargs['ansible_version']
        self.playbook_path = os.path.expanduser(kwargs['playbook_path'])
        self.playbooks = kwargs['playbooks']

    @staticmethod
    def load_file(path, **kwargs):
        """
        Load yaml manifest and override with any supplied arguments.
        """
        dct = yaml.safe_load(file(path, 'r'))
        dct.update(kwargs)
        return UrsulaManifest(**dct)
