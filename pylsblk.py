#!/usr/bin/env python
# -*- coding: utf-8 -*-
# (c) 2019, xiaomu <xiaomudk@gmail.com>
#
# 根据系统盘符读取到真实的磁盘
#

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

import os
import re
import json
import argparse
from collections import OrderedDict
from subprocess import check_call, check_output, CalledProcessError, STDOUT
import sys
try:
    from subprocess import DEVNULL  # py3k
except ImportError:
    DEVNULL = open(os.devnull, 'wb')

RAID_VENDOR_MAP = {
    "Dell": "/opt/MegaRAID/perccli/perccli64",
    "Other": "/opt/MegaRAID/storcli/storcli64",
}

DISK_FILTERS = OrderedDict([
    ('name', {'help_text': 'device name'}),
    ('kname',  {'help_text': 'internal kernel device name'}),
    ('maj:min', {'help_text': 'major:minor device number'}),
    ('fstype', {'help_text': 'filesystem type'}),
    ('mountpoint', {'help_text': 'where the device is mounted'}),
    ('label', {'help_text': 'filesystem label'}),
    ('uuid', {'help_text': 'filesystem uuid'}),
    ('partlabel', {'help_text': 'partition label'}),
    ('partuuid', {'help_text': 'partition uuid'}),
    ('ra', {'help_text': 'read-ahead of the device'}),
    ('ro', {'help_text': 'read-only device'}),
    ('rm', {'help_text': 'removable device'}),
    ('model', {'help_text': 'device identifier'}),
    ('serial', {'help_text': 'disk serial number'}),
    ('size', {'help_text': 'size of the device'}),
    ('state', {'help_text': 'state of the device'}),
    ('owner', {'help_text': 'user name'}),
    ('group', {'help_text': 'group name'}),
    ('mode', {'help_text': 'device node permissions'}),
    ('alignment', {'help_text': 'alignment offset'}),
    ('min-io', {'help_text': 'minimum i/o size'}),
    ('opt-io', {'help_text': 'optimal i/o size'}),
    ('phy-sec', {'help_text': 'physical sector size'}),
    ('log-sec', {'help_text': 'logical sector size'}),
    ('rota', {'help_text': 'rotational device'}),
    ('sched', {'help_text': 'i/o scheduler name'}),
    ('rq-size', {'help_text': 'request queue size'}),
    ('type', {'help_text': 'device type'}),
    ('disc-aln', {'help_text': 'discard alignment offset'}),
    ('disc-gran', {'help_text': 'discard granularity'}),
    ('disc-max', {'help_text': 'discard max bytes'}),
    ('disc-zero', {'help_text': 'discard zeroes data'}),
    ('wsame', {'help_text': 'write same max bytes'}),
    ('wwn', {'help_text': 'unique storage identifier'}),
    ('rand', {'help_text': 'adds randomness'}),
    ('pkname', {'help_text': 'internal parent kernel device name'}),
    ('hctl', {'help_text': 'host:channel:target:lun for scsi'}),
    ('tran', {'help_text': 'device transport type'}),
    ('rev', {'help_text': 'device revision'}),
    ('vendor', {'help_text': 'device vendor'}),
])

EXTRA_DISK_FILTERS = OrderedDict([
    ('slot', {'help_text': 'device slot'}),
    ('raid', {'help_text': 'device raid type'}),
])


def _print_message(message, file=None):
    """
    """
    if message:
        if file is None:
            file = sys.stdout
        file.write(message)


def _exit(status=0, message=None):
    """
    """
    if message:
        _print_message(message, sys.stderr)
    sys.exit(status)


def getstatusoutput(cmd):
    try:
        data = check_output(cmd, shell=True, universal_newlines=True, stderr=STDOUT)
        status = 0
    except CalledProcessError as ex:
        data = ex.output
        status = ex.returncode
    if data[-1:] == '\n':
        data = data[:-1]
    return status, data


def getoutput(cmd):
    return getstatusoutput(cmd)[1]


def parseLogicalDevicesString():
    """
    Parse the output of ``/opt/MegaRAID/storcli/storcli64 /call/vall show all J``
    :param logicalDevicesString: logical devices string
    :type logicalDevicesString: str
    :returns: logical device id to :class:`LSILogicalDeviceInfo` mapping
    :rtype: dict
    """
    vd_devices = {}
    vd_properties = {}
    vd_pds = {}
    sn_vd_map = {}
    raid_controller_bin = get_raid_controller_bin()
    logical_devices = getoutput('{bin} /call/vall show all J'.format(bin=raid_controller_bin))
    for controller in json.loads(logical_devices).get('Controllers', []):
        if controller["Command Status"]["Status"] == "Success":

            deviceInfos = controller["Response Data"]
            for key, value in deviceInfos.items():
                if re.search("/c\d+/v\d+", key):
                    device_number = int(re.search("/c\d+/v(\d+)", key).group(1))
                    vd_devices[device_number] = value
                    
                elif re.search("VD\d+ Properties", key):
                    device_number = int(re.search("VD(\d+)", key).group(1))
                    vd_properties[device_number] = value
                    serial = value.get('SCSI NAA Id', None)
                    if serial:
                        sn_vd_map[serial] = device_number
                elif re.search("PDs for VD \d+", key):
                    device_number = int(re.search("PDs for VD (\d+)", key).group(1))
                    vd_pds[device_number] = value

    return sn_vd_map, vd_pds, vd_devices


def _build_disk_tree(columns=None, disk_path=None):
    """ Build Block device tree and gather information
        about all disks and partitions avaialbe in the system
    """

    sn_vd_map, vd_pds, vd_devices = {}, {}, {}
    _columns = [column for column in columns if column in DISK_FILTERS]
    _extra_columns = [column for column in columns if column in EXTRA_DISK_FILTERS]

    disk_list = []
    if not disk_path:
        disk_path = ''
    if _extra_columns or 'rota' in _columns:
        _columns.append('serial')
        if has_raid_controller():
            sn_vd_map, vd_pds, vd_devices = parseLogicalDevicesString()
    try:
        columns_str = ','.join(_columns).upper()
        lsblk_cmd = 'lsblk -d -a -n -r -b -o {columns_str} {disk_path}'.format(columns_str=columns_str,
                                                                               disk_path=disk_path)
        disk_info_list = getoutput(lsblk_cmd)

        for di in disk_info_list.split('\n'):
            params = [p.strip() for p in di.split(' ')]
            disk_info = dict(zip(_columns, params))
            # for some devices we have empty size field,
            # use 0 instead
            if 'size' in _columns:
                disk_info['size'] = disk_info['size'] or 0
            if 'rota' in _columns and disk_info['serial']:
                serial = disk_info['serial']
                vd = sn_vd_map.get(serial, None)
                if vd:
                    physical_dick = vd_pds[vd]
                    is_hdd = len([x for x in physical_dick if x['Med'] != 'SSD']) > 0
                    if is_hdd:
                        disk_info['rota'] = 1
                    else:
                        disk_info['rota'] = 0
            if 'slot' in _extra_columns and disk_info['serial']:
                serial = disk_info['serial']
                vd = sn_vd_map.get(serial, None)
                if vd is not None:
                    physical_dick = vd_pds[vd]
                    slot_list = [str(x['DID']) for x in physical_dick]
                    disk_info['slot'] = '-'.join(slot_list)
                else:
                    disk_info['slot'] = '-'
            if 'raid' in _extra_columns and disk_info['serial']:
                serial = disk_info['serial']
                vd = sn_vd_map.get(serial, None)
                if vd is not None:
                    physical_dick = vd_devices[vd]
                    raid_type = [str(x['TYPE']) for x in physical_dick]
                    disk_info['raid'] = '-'.join(raid_type)
                else:
                    disk_info['raid'] = '-'
            disk_list.append(disk_info)
    except (CalledProcessError, ValueError):
        pass

    return disk_list


def get_raid_controller_type():
    raid_controller_type = 'Other'

    if os.path.exists('/proc/scsi/scsi'):
        with open("/proc/scsi/scsi") as f:
            for line in f.readlines():
                s = re.search(r"Model: PERC", line)
                if s:
                    raid_controller_type = 'Dell'
                    break

    return raid_controller_type


def has_raid_controller():
    """
    check physical machine has raid controller
    :return: bool
    """
    try:
        check_call('lspci -D | grep -i raid', shell=True, stdout=DEVNULL, stderr=DEVNULL)
    except CalledProcessError:
        return False

    return True


def get_raid_controller_bin():
    raid_controller_bin = RAID_VENDOR_MAP.get(get_raid_controller_type())

    return raid_controller_bin


def parse_lsblk_columns(parser):
    columns_list = parser.split(',')
    unusual_columns = [c for c in columns_list if c not in DISK_FILTERS and c not in EXTRA_DISK_FILTERS]
    if unusual_columns:
        raise argparse.ArgumentTypeError("unknown column:%s " % ','.join(unusual_columns))
    return columns_list


def parse_args():
    epilog = []
    for k, v in DISK_FILTERS.items():
        epilog.append('{k}\t'.format(k=k))
        epilog.append('{v}\n'.format(v=v['help_text']))

    for k, v in EXTRA_DISK_FILTERS.items():
        epilog.append('{k}\t'.format(k=k))
        epilog.append('{v}\n'.format(v=v['help_text']))

    parser = argparse.ArgumentParser(epilog=''.join(epilog), formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-o', '--output', help='output columns', default='name', dest='columns',
                        type=parse_lsblk_columns)
    parser.add_argument('-n', '--noheadings', help="don't print headings", action='store_true')
    parser.add_argument('disk_path', nargs=argparse.REMAINDER)
    return parser.parse_args()


def main():
    args = parse_args()
    disk_list = _build_disk_tree(list(args.columns), ' '.join(args.disk_path))

    if args.noheadings is False:
        for columns in args.columns:
            _print_message(message=columns)
            _print_message(message='\t')
        _print_message(message='\n')
    for disk in disk_list:
        for columns in args.columns:
            _print_message(message=str(disk[columns]))
            _print_message(message='\t')
        _print_message(message='\n')


if __name__ == '__main__':
    main()
