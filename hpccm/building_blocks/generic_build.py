# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=invalid-name, too-few-public-methods
# pylint: disable=too-many-instance-attributes

"""Generic build building block"""

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function

import posixpath
import re

import hpccm.templates.downloader
import hpccm.templates.rm

from hpccm.building_blocks.base import bb_base
from hpccm.primitives.comment import comment
from hpccm.primitives.copy import copy
from hpccm.primitives.shell import shell

class generic_build(bb_base, hpccm.templates.downloader, hpccm.templates.rm):
    """The `generic_build` building block downloads and builds
    a specified package.

    # Parameters

    build: List of shell commands to run in order to build the
    package.  The working directory is the source directory.  The
    default is an empty list.

    branch: The git branch to clone.  Only recognized if the
    `repository` parameter is specified.  The default is empty, i.e.,
    use the default branch for the repository.

    commit: The git commit to clone.  Only recognized if the
    `repository` parameter is specified.  The default is empty, i.e.,
    use the latest commit on the default branch for the repository.

    directory: The source code location.  The default value is the
    basename of the downloaded package.  If the value is not an
    absolute path, then the temporary working directory is prepended.

    install: List of shell commands to run in order to install the
    package.  The working directory is the source directory.  If
    `prefix` is defined, it will be automatically created if the list
    is non-empty.  The default is an empty list.

    prefix: The top level install location.  The default value is
    empty. If defined then the location is copied as part of the
    runtime method.

    recursive: Initialize and checkout git submodules. `repository` parameter
    must be specified. The default is False.

    repository: The git repository of the package to build.  One of
    this paramter or the `url` parameter must be specified.

    url: The URL of the tarball package to build.  One of this
    parameter or the `repository` parameter must be specified.

    # Examples

    ```python
    generic_build(build=['make ARCH=sm_70'],
                  install=['cp stream /usr/local/bin/cuda-stream'],
                  repository='https://github.com/bcumming/cuda-stream')
    ```

    """

    def __init__(self, **kwargs):
        """Initialize building block"""

        super(generic_build, self).__init__(**kwargs)

        self.__build = kwargs.get('build', [])
        self.__directory = kwargs.get('directory', None)
        self.__install = kwargs.get('install', [])
        self.__prefix = kwargs.get('prefix', None)
        self.__recursive = kwargs.get('recursive', False)

        self.__commands = [] # Filled in by __setup()
        self.__wd = '/var/tmp' # working directory

        # Construct the series of steps to execute
        self.__setup()

        # Fill in container instructions
        self.__instructions()

    def __instructions(self):
        """Fill in container instructions"""

        if self.url:
            self += comment(self.url, reformat=False)
        elif self.repository:
            self += comment(self.repository, reformat=False)
        self += shell(commands=self.__commands)

    def __setup(self):
        """Construct the series of shell commands, i.e., fill in
           self.__commands"""

        # Get source
        self.__commands.append(self.download_step(recursive=self.__recursive,
                                                  wd=self.__wd))

        # directory containing the unarchived package
        if self.__directory:
            if posixpath.isabs(self.__directory):
                self.src_directory = self.__directory
            else:
                self.src_directory = posixpath.join(self.__wd,
                                                    self.__directory)

        # Build
        if self.__build:
            self.__commands.append('cd {}'.format(self.src_directory))
            self.__commands.extend(self.__build)

        # Install
        if self.__install:
            if self.__prefix:
                self.__commands.append('mkdir -p {}'.format(self.__prefix))
            self.__commands.append('cd {}'.format(self.src_directory))
            self.__commands.extend(self.__install)

        # Cleanup
        remove = [self.src_directory]
        if self.url:
            remove.append(posixpath.join(self.__wd,
                                         posixpath.basename(self.url)))
        self.__commands.append(self.cleanup_step(items=remove))

    def runtime(self, _from='0'):
        """Generate the set of instructions to install the runtime specific
        components from a build in a previous stage.

        # Examples

        ```python
        g = generic_build(...)
        Stage0 += g
        Stage1 += g.runtime()
        ```
        """
        if self.__prefix:
            instructions = []
            if self.url:
                instructions.append(comment(self.url, reformat=False))
            elif self.repository:
                instructions.append(comment(self.repository, reformat=False))
            instructions.append(copy(_from=_from, src=self.__prefix,
                                     dest=self.__prefix))
            return '\n'.join(str(x) for x in instructions)
        else:
            return
