#
# Project Ginger Base
#
# Copyright IBM Corp, 2016
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

import mock
import unittest

from wok.exception import NotFoundError, OperationFailed
from wok.plugins.gingerbase.disks import _get_lsblk_devs
from wok.plugins.gingerbase.disks import pvs_with_vg_list


class DiskTests(unittest.TestCase):

    @mock.patch('wok.plugins.gingerbase.disks.run_command')
    def test_lsblk_returns_404_when_device_not_found(self, mock_run_command):
        mock_run_command.return_value = ["", "not a block device", 32]
        fake_dev = "/not/a/true/block/dev"
        keys = ["MOUNTPOINT"]

        with self.assertRaises(NotFoundError):
            _get_lsblk_devs(keys, [fake_dev])
            cmd = ['lsblk', '-Pbo', 'MOUNTPOINT', fake_dev]
            mock_run_command.assert_called_once_with(cmd)

    @mock.patch('wok.plugins.gingerbase.disks.run_command')
    def test_lsblk_returns_500_when_unknown_error_occurs(
            self, mock_run_command):

        mock_run_command.return_value = ["", "", 1]
        valid_dev = "/valid/block/dev"
        keys = ["MOUNTPOINT"]

        with self.assertRaises(OperationFailed):
            _get_lsblk_devs(keys, [valid_dev])
            cmd = ['lsblk', '-Pbo', 'MOUNTPOINT', valid_dev]
            mock_run_command.assert_called_once_with(cmd)

    @mock.patch('wok.plugins.gingerbase.disks.run_command')
    def test_pvs_with_vg_list(self, mock_run_command):
        mock_run_command.return_value = ["""
        /dev/mapper/36005076307ffc6a60000000000001f22 vpoolfclun2
  /dev/mapper/36005076307ffc6a60000000000001f23 vpoolfclun
  /dev/dasdb1""", "", 0]
        outlist = pvs_with_vg_list()
        self.assertEqual(outlist[0].get('/dev/dasdb1'), 'N/A')
