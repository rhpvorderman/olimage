import logging
import os
import shlex
import shutil
import tarfile

from .stamper import PackageStamper
from .util import Util
from .worker import Worker


logger = logging.getLogger(__name__)


class Builder(Util):

    def __init__(self, name, config):
        super().__init__(name, config)

        # Configure stamper
        self.stamper = PackageStamper(self.paths['build'])

    def extract(self):

        path = self.paths['extract']
        if 'extracted' in self.stamper.stamps and os.path.exists(path):
            return self

        self.stamper.remove()

        # Cleanup directory
        if os.path.exists(path):
            logger.debug("Removing dirty directory: {}".format(self.paths['extract']))
            shutil.rmtree(path)

        # Extract sources
        with tarfile.open(name=self.paths['archive'], mode='r:gz') as tar:
            tar.extractall(path=self.paths['extract'])

        self.stamper.stamp('extracted')

        return self

    def patch(self, patches):
        if 'patched' in self.stamper.stamps:
            return

        if not os.path.exists(patches):
            self._builder.stamper.stamp('patched')
            return

        logger.info("Applying patches from {}".format(patches))
        Worker.run(
            ["cd {}; QUILT_PATCHES={} quilt push".format(self.paths['extract'], patches)],
            logger,
            shell=True
        )

        self.stamper.stamp('patched')

    def make(self, command, **kwargs):
        return Worker.run(
            shlex.split("/bin/bash -c 'make -C {} {} -j{}'".format(
                self.paths['extract'],
                command,
                1 if os.cpu_count() is None else os.cpu_count())
            ),
            logger
        )
