#
# Project Ginger Base
#
# Copyright IBM Corp, 2015-2016
#
# Code derived from Project Kimchi
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA

import copy
import os
import time
import urlparse
from ConfigParser import ConfigParser

from wok.basemodel import Singleton
from wok.exception import InvalidOperation, InvalidParameter
from wok.exception import OperationFailed, NotFoundError, MissingParameter

from wok.plugins.gingerbase.config import gingerBaseLock
from wok.plugins.gingerbase.utils import validate_repo_url
from wok.plugins.gingerbase.yumparser import get_yum_repositories
from wok.plugins.gingerbase.yumparser import write_repo_to_file
from wok.plugins.gingerbase.yumparser import get_display_name
from wok.plugins.gingerbase.yumparser import get_expanded_url


class Repositories(object):
    __metaclass__ = Singleton

    """
    Class to represent and operate with repositories information.
    """
    def __init__(self):
        try:
            __import__('dnf')
            self._pkg_mnger = YumRepo()
        except ImportError:
            try:
                __import__('yum')
                self._pkg_mnger = YumRepo()
            except ImportError:
                try:
                    __import__('apt_pkg')
                    self._pkg_mnger = AptRepo()
                except ImportError:
                    raise InvalidOperation('GGBREPOS0014E')

    def addRepository(self, params):
        """
        Add and enable a new repository
        """
        config = params.get('config', {})
        extra_keys = list(
            set(config.keys()).difference(set(self._pkg_mnger.CONFIG_ENTRY)))
        if len(extra_keys) > 0:
            raise InvalidParameter("GGBREPOS0028E",
                                   {'items': ",".join(extra_keys)})

        return self._pkg_mnger.addRepo(params)

    def getRepositories(self):
        """
        Return a dictionary with all Ginger Base repositories. Each element
        uses the format {<repo_id>: {repo}}, where repo is a dictionary in the
        repositories.Repositories() format.
        """
        return self._pkg_mnger.getRepositoriesList()

    def getRepository(self, repo_id):
        """
        Return a dictionary with all info from a given repository ID.
        """
        info = self._pkg_mnger.getRepo(repo_id)
        info['repo_id'] = repo_id
        return info

    def enableRepository(self, repo_id):
        """
        Enable a repository.
        """
        return self._pkg_mnger.toggleRepo(repo_id, True)

    def disableRepository(self, repo_id):
        """
        Disable a given repository.
        """
        return self._pkg_mnger.toggleRepo(repo_id, False)

    def updateRepository(self, repo_id, params):
        """
        Update the information of a given repository.
        The input is the repo_id of the repository to be updated and a dict
        with the information to be updated.
        """
        return self._pkg_mnger.updateRepo(repo_id, params)

    def removeRepository(self, repo_id):
        """
        Remove a given repository
        """
        return self._pkg_mnger.removeRepo(repo_id)


class YumRepo(object):
    """
    Class to represent and operate with YUM repositories.
    It's loaded only on those systems listed at YUM_DISTROS and loads necessary
    modules in runtime.
    """
    TYPE = 'yum'
    DEFAULT_CONF_DIR = "/etc/yum.repos.d"
    CONFIG_ENTRY = ('repo_name', 'mirrorlist', 'metalink')

    def __init__(self):
        self._confdir = self.DEFAULT_CONF_DIR

    def _get_repos(self, errcode):
        try:
            gingerBaseLock.acquire()
            repos = get_yum_repositories()
        except Exception, e:
            gingerBaseLock.release()
            raise OperationFailed(errcode, {'err': str(e)})
        finally:
            gingerBaseLock.release()

        return repos

    def getRepositoriesList(self):
        """
        Return a list of repositories IDs
        """
        repos = self._get_repos('GGBREPOS0024E')
        return repos.keys()

    def getRepo(self, repo_id):
        """
        Return a dictionary in the repositories.Repositories() of the given
        repository ID format with the information of a YumRepository object.
        """
        repos = self._get_repos('GGBREPOS0025E')

        if repo_id not in repos.keys():
            raise NotFoundError("GGBREPOS0012E", {'repo_id': repo_id})

        entry = repos.get(repo_id)

        display_name = get_display_name(entry.name)

        info = {}
        info['enabled'] = entry.enabled
        info['baseurl'] = entry.baseurl or ''
        info['config'] = {}
        info['config']['display_repo_name'] = display_name
        info['config']['repo_name'] = entry.name or ''
        info['config']['gpgcheck'] = entry.gpgcheck
        info['config']['gpgkey'] = entry.gpgkey or ''
        info['config']['mirrorlist'] = entry.mirrorlist or ''
        info['config']['metalink'] = entry.metalink or ''
        return info

    def addRepo(self, params):
        """
        Add a given repository to YumBase
        """
        # At least one base url, or one mirror, must be given.
        baseurl = params.get('baseurl', '')

        config = params.get('config', {})
        mirrorlist = config.get('mirrorlist', '')
        metalink = config.get('metalink', '')
        if not baseurl and not mirrorlist and not metalink:
            raise MissingParameter("GGBREPOS0013E")

        if baseurl:
            validate_repo_url(get_expanded_url(baseurl))

        if mirrorlist:
            validate_repo_url(get_expanded_url(mirrorlist))

        if metalink:
            validate_repo_url(get_expanded_url(metalink))

        if mirrorlist and metalink:
            raise InvalidOperation('GGBREPOS0030E')

        repo_id = params.get('repo_id', None)
        if repo_id is None:
            repo_id = "gingerbase_repo_%s" % str(int(time.time() * 1000))

        repos = self._get_repos('GGBREPOS0026E')
        if repo_id in repos.keys():
            raise InvalidOperation("GGBREPOS0022E", {'repo_id': repo_id})

        repo_name = config.get('repo_name', repo_id)
        repo = {'baseurl': baseurl, 'mirrorlist': mirrorlist,
                'name': repo_name, 'gpgcheck': 1,
                'gpgkey': [], 'enabled': 1, 'metalink': metalink}

        # write a repo file in the system with repo{} information.
        parser = ConfigParser()
        parser.add_section(repo_id)

        for key, value in repo.iteritems():
            if value:
                parser.set(repo_id, key, value)

        repofile = os.path.join(self._confdir, repo_id + '.repo')
        try:
            with open(repofile, 'w') as fd:
                parser.write(fd)
        except:
            raise OperationFailed("GGBREPOS0018E",
                                  {'repo_file': repofile})

        return repo_id

    def toggleRepo(self, repo_id, enable):
        repos = self._get_repos('GGBREPOS0011E')
        if repo_id not in repos.keys():
            raise NotFoundError("GGBREPOS0012E", {'repo_id': repo_id})

        entry = repos.get(repo_id)
        if enable and entry.enabled:
            raise InvalidOperation("GGBREPOS0015E", {'repo_id': repo_id})

        if not enable and not entry.enabled:
            raise InvalidOperation("GGBREPOS0016E", {'repo_id': repo_id})

        gingerBaseLock.acquire()
        try:
            if enable:
                entry.enable()
            else:
                entry.disable()

            write_repo_to_file(entry)
        except:
            if enable:
                raise OperationFailed("GGBREPOS0020E", {'repo_id': repo_id})

            raise OperationFailed("GGBREPOS0021E", {'repo_id': repo_id})
        finally:
            gingerBaseLock.release()

        return repo_id

    def updateRepo(self, repo_id, params):
        """
        Update a given repository in repositories.Repositories() format
        """
        repos = self._get_repos('GGBREPOS0011E')
        if repo_id not in repos.keys():
            raise NotFoundError("GGBREPOS0012E", {'repo_id': repo_id})

        entry = repos.get(repo_id)

        baseurl = params.get('baseurl', entry.baseurl)
        config = params.get('config', {})
        mirrorlist = config.get('mirrorlist', entry.mirrorlist)
        metalink = config.get('metalink', entry.metalink)

        if baseurl is not None and len(baseurl.strip()) == 0:
            baseurl = None

        if mirrorlist is not None and len(mirrorlist.strip()) == 0:
            mirrorlist = None

        if metalink is not None and len(metalink.strip()) == 0:
            metalink = None

        if baseurl is None and mirrorlist is None and metalink is None:
            raise MissingParameter("GGBREPOS0013E")

        if baseurl is not None:
            validate_repo_url(get_expanded_url(baseurl))
            entry.baseurl = baseurl

        if mirrorlist is not None:
            validate_repo_url(get_expanded_url(mirrorlist))
            entry.mirrorlist = mirrorlist

        if metalink is not None:
            validate_repo_url(get_expanded_url(metalink))
            entry.metalink = metalink

        if mirrorlist and metalink:
            raise InvalidOperation('GGBREPOS0030E')

        entry.id = params.get('repo_id', repo_id)
        entry.name = config.get('repo_name', entry.name)
        entry.gpgcheck = config.get('gpgcheck', entry.gpgcheck)
        entry.gpgkey = config.get('gpgkey', entry.gpgkey)
        gingerBaseLock.acquire()
        write_repo_to_file(entry)
        gingerBaseLock.release()
        return repo_id

    def removeRepo(self, repo_id):
        """
        Remove a given repository
        """
        repos = self._get_repos('GGBREPOS0027E')
        if repo_id not in repos.keys():
            raise NotFoundError("GGBREPOS0012E", {'repo_id': repo_id})

        entry = repos.get(repo_id)
        parser = ConfigParser()
        with open(entry.repofile) as fd:
            parser.readfp(fd)

        if len(parser.sections()) == 1:
            os.remove(entry.repofile)
            return

        parser.remove_section(repo_id)
        with open(entry.repofile, "w") as fd:
            parser.write(fd)


class AptRepo(object):
    """
    Class to represent and operate with YUM repositories.
    It's loaded only on those systems listed at YUM_DISTROS and loads necessary
    modules in runtime.
    """
    TYPE = 'deb'
    GINGERBASE_LIST = "gingerbase-source.list"
    CONFIG_ENTRY = ('dist', 'comps')

    def __init__(self):
        getattr(__import__('apt_pkg'), 'init_config')()
        getattr(__import__('apt_pkg'), 'init_system')()
        config = getattr(__import__('apt_pkg'), 'config')
        module = __import__('aptsources.sourceslist', globals(), locals(),
                            ['SourcesList'], -1)

        self._sourceparts_path = '/%s/%s' % (
            config.get('Dir::Etc'), config.get('Dir::Etc::sourceparts'))
        self._sourceslist = getattr(module, 'SourcesList')
        self.filename = os.path.join(self._sourceparts_path,
                                     self.GINGERBASE_LIST)
        if not os.path.exists(self.filename):
            with open(self.filename, 'w') as fd:
                fd.write("# This file is managed by Ginger Base and it "
                         "must not be modified manually\n")

    def _get_repos(self):
        try:
            repos = self._sourceslist()
        except Exception, e:
            raise OperationFailed('GGBREPOS0025E', {'err': e.message})

        return repos

    def _get_repo_id(self, repo):
        data = urlparse.urlparse(repo.uri)
        name = data.hostname or data.path
        return '%s-%s-%s' % (name, repo.dist, "-".join(repo.comps))

    def _get_source_entry(self, repo_id):
        gingerBaseLock.acquire()
        try:
            repos = self._get_repos()
        except OperationFailed:
            raise
        finally:
            gingerBaseLock.release()

        for r in repos:
            # Ignore deb-src repositories
            if r.type != 'deb':
                continue

            if self._get_repo_id(r) != repo_id:
                continue

            return r

        return None

    def getRepositoriesList(self):
        """
        Return a list of repositories IDs

        APT repositories there aren't the concept about repository ID, so for
        internal control, the repository ID will be built as described in
        _get_repo_id()
        """
        gingerBaseLock.acquire()
        try:
            repos = self._get_repos()
        except OperationFailed:
            raise
        finally:
            gingerBaseLock.release()

        res = []
        for r in repos:
            # Ignore deb-src repositories
            if r.type != 'deb':
                continue

            res.append(self._get_repo_id(r))

        return res

    def getRepo(self, repo_id):
        """
        Return a dictionary in the repositories.Repositories() format of the
        given repository ID with the information of a SourceEntry object.
        """
        r = self._get_source_entry(repo_id)
        if r is None:
            raise NotFoundError("GGBREPOS0012E", {'repo_id': repo_id})

        info = {'enabled': not r.disabled,
                'baseurl': r.uri,
                'config': {'dist': r.dist,
                           'comps': r.comps}}
        return info

    def addRepo(self, params):
        """
        Add a new APT repository based on <params>
        """
        # To create a APT repository the dist is a required parameter
        # (in addition to baseurl, verified on controller through API.json)
        config = params.get('config', None)
        if config is None:
            raise MissingParameter("GGBREPOS0019E")

        if 'dist' not in config.keys():
            raise MissingParameter("GGBREPOS0019E")

        uri = params['baseurl']
        dist = config['dist']
        comps = config.get('comps', [])

        validate_repo_url(get_expanded_url(uri))

        gingerBaseLock.acquire()
        try:
            repos = self._get_repos()
            source_entry = repos.add('deb', uri, dist, comps,
                                     file=self.filename)
            repos.save()
        except Exception as e:
            raise OperationFailed("GGBREPOS0026E", {'err': e.message})
        finally:
            gingerBaseLock.release()
        return self._get_repo_id(source_entry)

    def toggleRepo(self, repo_id, enable):
        """
        Enable a given repository
        """
        r = self._get_source_entry(repo_id)
        if r is None:
            raise NotFoundError("GGBREPOS0012E", {'repo_id': repo_id})

        if enable and not r.disabled:
            raise InvalidOperation("GGBREPOS0015E", {'repo_id': repo_id})

        if not enable and r.disabled:
            raise InvalidOperation("GGBREPOS0016E", {'repo_id': repo_id})

        if enable:
            line = 'deb'
        else:
            line = '#deb'

        gingerBaseLock.acquire()
        try:
            repos = self._get_repos()
            repos.remove(r)
            repos.add(line, r.uri, r.dist, r.comps, file=self.filename)
            repos.save()
        except:
            if enable:
                raise OperationFailed("GGBREPOS0020E", {'repo_id': repo_id})

            raise OperationFailed("GGBREPOS0021E", {'repo_id': repo_id})
        finally:
            gingerBaseLock.release()

        return repo_id

    def updateRepo(self, repo_id, params):
        """
        Update a given repository in repositories.Repositories() format
        """
        old_info = self.getRepo(repo_id)
        updated_info = copy.deepcopy(old_info)
        updated_info['baseurl'] = params.get(
            'baseurl', updated_info['baseurl'])

        if 'config' in params.keys():
            config = params['config']
            updated_info['config']['dist'] = config.get(
                'dist', old_info['config']['dist'])
            updated_info['config']['comps'] = config.get(
                'comps', old_info['config']['comps'])

        self.removeRepo(repo_id)
        try:
            return self.addRepo(updated_info)
        except:
            self.addRepo(old_info)
            raise

    def removeRepo(self, repo_id):
        """
        Remove a given repository
        """
        r = self._get_source_entry(repo_id)
        if r is None:
            raise NotFoundError("GGBREPOS0012E", {'repo_id': repo_id})

        gingerBaseLock.acquire()
        try:
            repos = self._get_repos()
            repos.remove(r)
            repos.save()
        except:
            raise OperationFailed("GGBREPOS0017E", {'repo_id': repo_id})
        finally:
            gingerBaseLock.release()
