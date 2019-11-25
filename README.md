# pylsblk
  
  对lsblk对了封装，适配磁盘做raid的情况
  可以真实的获取磁盘HDD或SSD类型、磁盘raid类型、磁盘插槽位置

  ### install 
  
  ##### 1. install storcli
  
  dell machine
  
  ```
  https://downloads.dell.com/FOLDER05235308M/1/perccli_linux_NF8G9_A07_7.529.00.tar.gz
  tar xf perccli_linux_NF8G9_A07_7.529.00.tar.gz
  rpm -ivh perccli_*/Linux/*.rpm
  ```
  
  other machine
  
  ```
  wget https://docs.broadcom.com/docs-and-downloads/syncro-shared-storage/downloads/1-15-05_StorCLI.zip
  unzip 1-15-05_StorCLI.zip
  unzip storcli_all_os.zip
  rpm -ivh storcli_all_os/Linux/storcli-1.15.05-1.noarch.rpm
  ```
  
  ##### 2. install pylsblk
  
  ```
  wget https://raw.githubusercontent.com/xiaomudk/pylsblk/master/pylsblk.py -O pylsblk.py
  chmod +x pylsblk.py
  ```
  
  ### usage
  
  ```
  usage: pylsblk.py [-h] [-o COLUMNS] [-n] ...

positional arguments:
  disk_path

optional arguments:
  -h, --help            show this help message and exit
  -o COLUMNS, --output COLUMNS
                        output columns
  -n, --noheadings      don't print headings

name    device name
kname   internal kernel device name
maj:min major:minor device number
fstype  filesystem type
mountpoint      where the device is mounted
label   filesystem label
uuid    filesystem uuid
partlabel       partition label
partuuid        partition uuid
ra      read-ahead of the device
ro      read-only device
rm      removable device
model   device identifier
serial  disk serial number
size    size of the device
state   state of the device
owner   user name
group   group name
mode    device node permissions
alignment       alignment offset
min-io  minimum i/o size
opt-io  optimal i/o size
phy-sec physical sector size
log-sec logical sector size
rota    rotational device
sched   i/o scheduler name
rq-size request queue size
type    device type
disc-aln        discard alignment offset
disc-gran       discard granularity
disc-max        discard max bytes
disc-zero       discard zeroes data
wsame   write same max bytes
wwn     unique storage identifier
rand    adds randomness
pkname  internal parent kernel device name
hctl    host:channel:target:lun for scsi
tran    device transport type
rev     device revision
vendor  device vendor
slot    device slot
raid    device raid type
  ```
  
  ### example
  
  ```
  # pylsblk.py -o name,rota,slot,raid
name    rota    slot    raid
sda     1       12-13   RAID1
sdb     1       0       RAID0
sdc     0       1       RAID0
sdd     0       2       RAID0
sde     1       3       RAID0
sdf     1       4       RAID0
  ```