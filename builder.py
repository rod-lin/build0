import book
import os

CONF_SOURCES_DIR = "sources"
CONF_TOOLS_DIR = "tools"

CONF_WORK_SCRIPTS_DIR = "scripts"
CONF_WORK_FLAGS_DIR = "flags"

CONF_WORK_PROG_SH = "progress.sh"

PROGRESS_SH = b"""#!/bin/bash

if [ -z "$1" ]; then
    echo "need one argument"
    exit 1
fi

beautify_date() {
    date -d@$1 -u +%H:%M:%S
}

progress() {
    SECONDS=0
    while true; do
        echo -ne "\\rtime elapsed: `beautify_date $SECONDS`"
        sleep 0.5
    done
}

wait() {
    while [ -e /proc/$1 ]; do
        sleep 0.1
    done
}

progress &
PROG_PID=$!

bash -c "$1"
EXIT=$?

kill $PROG_PID # kill progress
echo ""

if [ $EXIT != 0 ]; then
    exit 1
fi
"""

# need to set global var
# LFS
# LFS_TGT

class Builder:
    def __init__(self, config):
        self.conf_root = os.path.realpath(config["general"]["root"])
        self.conf_rev = config["general"]["revision"]
        self.conf_book = config["general"]["book"]
        self.conf_target = config["general"]["target"]
        
        self.conf_sources = self.conf_root + "/" + CONF_SOURCES_DIR
        self.conf_tools = self.conf_root + "/" + CONF_TOOLS_DIR
        self.conf_work = self.conf_root + "/" + config["general"]["work-dir"]
        self.conf_work_scripts = self.conf_work + "/" + CONF_WORK_SCRIPTS_DIR
        self.conf_work_flags = self.conf_work + "/" + CONF_WORK_FLAGS_DIR

        self.book = book.Book(self.conf_book)

        if "download" in config:
            if "use-mirror" in config["download"]:
                self.conf_mirror = config["download"]["use-mirror"] + self.book.version + "/"
            else:
                self.conf_mirror = None

        if "build" in config:
            if "make-job" in config["build"]:
                self.conf_make_job = config["build"]["make-job"]
            else:
                self.conf_make_job = None

        def script_alter(scripts):
            scripts = list(filter(lambda a: a.type != "test", scripts))

            if self.conf_make_job is not None:
                for cmd in scripts:
                    if cmd.cmd == "make":
                        cmd.cmd = "make -j" + str(self.conf_make_job)

            # print(scripts)

            return scripts

        self.book.map_script(script_alter)

    def init_root(self):
        if os.path.isdir(self.conf_root):
            if not os.path.isdir(self.conf_sources):
                raise Exception("root " + self.conf_root + " exists")

        def mkdir(dir):
            if not os.path.isdir(dir):
                os.mkdir(dir)

        # create working directories
        mkdir(self.conf_root)
        mkdir(self.conf_sources)
        mkdir(self.conf_tools)
        mkdir(self.conf_work)
        mkdir(self.conf_work_scripts)
        mkdir(self.conf_work_flags)

        with open(self.conf_work + "/" + CONF_WORK_PROG_SH, "wb") as fp:
            fp.write(PROGRESS_SH)

        symlink = "/" + CONF_TOOLS_DIR

        # create symlink /tools
        if os.path.exists(symlink):
            if os.path.realpath(os.readlink(symlink)) != self.conf_tools:
                raise Exception("symlink exists but points to different directory")
        else:
            if os.system("sudo ln -sT '{}' '{}'".format(self.conf_tools, symlink)) != 0:
                raise Exception("failed to create /tools symlink")

    def download_sources(self):
        for package in self.book.packages:
            if not package.save_to(self.conf_sources, mirror_prefix = self.conf_mirror):
                raise Exception("failed to fetch package " + str(package))

        for patch in self.book.patches:
            if not patch.save_to(self.conf_sources, mirror_prefix = self.conf_mirror):
                raise Exception("failed to fetch patch" + str(patch))

    def gen_env_header(self):
        return "LFS='{}' LFS_TGT='{}' PATH=/tools/bin:${{PATH}}".format(self.conf_root, self.conf_target)

    # generate makefile for toolchain
    def gen_toolchain_makefile(self):
        # def tar_param(fname):
        #     ext = os.path.splitext(fname)[1]
        #     map = {
        #         ".gz": "z",
        #         ".tgz": "z",
        #         ".xz": "J",
        #         ".txz": "J",
        #         ".bz": "j",
        #         ".tbz": "j"
        #     }

        #     if ext in map:
        #         return map[ext]
        #     else:
        #         raise Exception("unrecognized compression for " + fname)

        def strip_ext(fname):
            fname, ext = os.path.splitext(fname)
            if ext == "" or ext == ".tar" or ext == ".tgz" or ext == ".txz" or ext == ".tbz": return fname
            else: return strip_ext(fname)

        targets = []
        makefile = []

        for step in self.book.toolchain_steps:
            id = step.id()
            script = step.gen_build_script()
            fname = self.conf_work_scripts + "/" + id + ".sh"

            package_fname = self.conf_sources + "/" + step.package.file
            # param = tar_param(step.package.file)

            with open(fname, "wb") as fp:
                fp.write(script.encode("utf-8"))

            # create tmp directory
            # tmp
            # tar -xf file -C tmp
            # mv tmp/* ./build

            mf_trunk = \
                "{target}: {package}{dep}\n\t" + \
                "\n\t".join([
                    "@echo '#############################'",
                    "@echo preparing {step_name}",
                    "@rm -rf '{sources}/tmp' '{sources}/build'",
                    "@mkdir '{sources}/tmp'",
                    "@tar -xf '{package}' -C '{sources}/tmp'",
                    "@mv '{sources}/tmp'/* '{sources}/build'",
                    "@echo building {step_name}, estimated {sbu}",
                    "@bash {progress} \"cd '{sources}/build' && {header} bash {script} 1>/dev/null 2>/dev/null\"",
                    "@echo built {step_name}",
                    "@rm -rf '{sources}/tmp' '{sources}/build'",
                    "@touch '{target}'"
                ])

            target = self.conf_work_flags + "/build-" + id

            mf_trunk = mf_trunk.format(
                sources = self.conf_sources,
                package = package_fname, id = id,
                script = fname,
                header = self.gen_env_header(),
                flags = self.conf_work_flags,
                target = target,
                dep = " " + targets[-1] if len(targets) else "",
                # source_dir = strip_ext(package_fname),
                progress = self.conf_work + "/" + CONF_WORK_PROG_SH,
                step_name = step.name,
                sbu = step.sbu)

            targets.append(target)
            makefile.append(mf_trunk)

        last_target = " " + targets[-1] if len(targets) else ""

        with open(self.conf_work + "/makefile", "wb") as fp:
            fp.write(("all:" + last_target + "\n\n").encode("utf-8"))
            fp.write(("\n\n".join(makefile) + "\n").encode("utf-8"))
