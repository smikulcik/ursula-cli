import os
import shutil
import tempfile
import yaml

from subprocess import check_call

class UrsulaManifest(object):
    def __init__(self, **kwargs):
        self.ansible_version = kwargs['ansible_version']
        self.playbook_path = os.path.expanduser(kwargs['playbook_path'])
        self.playbooks = kwargs['playbooks']

        self.playbook_auto_fetch = False
        if 'playbook_auto_fetch' in kwargs:
            self.playbook_auto_fetch = kwargs['playbook_auto_fetch']

    def resolve_git_refs(self):
        """
        If the special ref 'dirty' is supplied, simply use the repository as-is.
        Otherwise, fetch and check out the supplied ref on the local URSULA_RUN
        branch, and do a branch-only clone to ensure a clean working directory.
        """
        for playbook in self.playbooks:
            repo = os.path.join(self.playbook_path, playbook['repository'])
            if not os.path.isdir(os.path.join(repo, '.git')):
                raise Exception("Repository %s not found in %s" %
                                (playbook['repository'], self.playbook_path))

            if playbook['git_ref'] == 'dirty':
                playbook['fullpath'] = os.path.join(repo, playbook['file'])
            else:
                original_cwd = os.getcwd()
                os.chdir(repo)
                if self.playbook_auto_fetch:
                    check_call(['git', 'fetch', '--all'])
                check_call(['git', 'branch', '-f', 'URSULA_RUN',
                            'origin/'+playbook['git_ref']])
                os.chdir(original_cwd)
                playbook['tempdir'] = tempfile.mkdtemp()
                check_call(['git', 'clone', '-b', 'URSULA_RUN', '--single-branch',
                            repo, playbook['tempdir']])
                playbook['fullpath'] = os.path.join(playbook['tempdir'], playbook['file'])

            if not os.path.isfile(playbook['fullpath']):
                raise Exception("Playbook %s/%s not found in %s" %
                                (playbook['repository'], playbook['file'],
                                self.playbook_path))

    def clean_git_tempdirs(self):
        for playbook in self.playbooks:
            if 'tempdir' in playbook:
                shutil.rmtree(playbook['tempdir'])


    @staticmethod
    def load_file(path, **kwargs):
        """
        Load yaml manifest and override with any supplied arguments.
        """
        dct = yaml.safe_load(file(path, 'r'))
        dct.update(kwargs)
        return UrsulaManifest(**dct)
