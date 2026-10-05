# -*- coding : utf-8 -*-
import os, sys


def mountpoint(path):
    status = os.system("mountpoint -q %s" % path)
    if status == 0:
        return True
    else:
        return False


def cgmanager_is_enabled():
    res = True

    enabled = set(os.listdir("/etc/mudur/services/enabled"))
    conditional = set(os.listdir("/etc/mudur/services/conditional"))
    enabled.union(conditional)

    if "cgmanager" not in enabled:
        res = False
    return res


class Controller:
    def __init__(self, subsysname, hierarchy, num_cgroups, enabled):
        self.subsysname = subsysname
        self.hierarchy = hierarchy
        self.num_cgroups = num_cgroups
        self.enabled = enabled

    def mount(self):
        if self.enabled == 1:
            os.chdir("/sys/fs/cgroup")
            if mountpoint(self.subsysname) == False:
                s = self.subsysname
                status = os.system(
                    "mkdir -p %s; mount -n -t cgroup -o %s cgroup %s" % (s, s, s)
                )
                if status == 0:
                    return True
                else:
                    return False


class Cgroupfs:
    def __init__(self, logger=None):
        self.controllers = {}
        self.logger = logger
        if self.check_fstab == True:
            print("cgroupfs in fstab, exiting.")
            sys.exit(-1)

        if self.kernel_support() == False:
            print("No kernel support for cgroupfs, exiting.")
            sys.exit(-2)

        if self.check_sysfs() == False:
            print("/sys/fs/cgroups directory not found, exiting")
            sys.exit(-3)

        self.mount_cgroup()
        self.find_controllers()

        if cgmanager_is_enabled() or self.mounted_version() < 2:
            for cname, c in self.controllers.items():
                c.mount()

    def check_fstab(self):
        found = False
        for line in open("/etc/fstab").readlines():
            if line[0] == "#":
                continue
            else:
                if line.find("cgroup"):
                    found = True
        return found

    def kernel_support(self):
        return os.path.isfile("/proc/cgroups")

    def check_sysfs(self):
        return os.path.isdir("/sys/fs/cgroup")

    def supported_version(self):
        ver = 1
        with open("/proc/filesystems") as file:
            fs = file.read()
            if fs.find("cgroup2") >= 0:
                ver = 2
            elif fs.find("cgroup") >= 0:
                ver = 1

        return ver

    def mounted_version(self):
        res = 1
        with open("/proc/mounts") as file:
            for line in file.readlines():
                parts = line.split()
                if parts[1] == "/sys/fs/cgroup":
                    if parts[2] == "cgroup2":
                        res = 2
                    break

        return res

    def mount_cgroup(self):
        if mountpoint("/sys/fs/cgroup") == False:
            if self.logger:
                self.logger.log(
                    "Supperted cgroup version: %s" % self.supported_version()
                )

            if cgmanager_is_enabled() or self.supported_version() == 1:
                cmd = "mount -t tmpfs -o uid=0,gid=0,mode=0755 cgroup /sys/fs/cgroup"
                msg = "Used cgroup version: 1."
                if cgmanager_is_enabled():
                    msg += " 'cgmanager' service enabled."
            else:
                msg = "Used cgroup version: 2."
                cmd = "mount -t cgroup2 -o uid=0,gid=0,mode=0755 none /sys/fs/cgroup"

            if self.logger:
                self.logger.log(msg)
            return os.system(cmd)

    def find_controllers(self):
        for line in open("/proc/cgroups").readlines():
            line = line.strip()
            if line[0] == "#":
                continue
            else:
                subsysname, hierarchy, num_cgroups, enabled = line.split()
                enb = int(enabled)
                hie = int(hierarchy)
                numc = int(num_cgroups)
                self.controllers[subsysname] = Controller(subsysname, hie, numc, enb)
