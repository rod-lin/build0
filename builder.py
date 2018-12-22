import book
import os

CONF_SOURCES_DIR = "sources"
CONF_TOOLS_DIR = "tools"

CONF_WORK_SCRIPTS_DIR = "scripts"
CONF_WORK_FLAGS_DIR = "flags"

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
        return "LFS='{}' LFS_TGT='{}'".format(self.conf_root, self.conf_target)

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

        makefile = []

        for step in self.book.toolchain_steps:
            id = step.id()
            script = step.gen_build_script()
            fname = self.conf_work_scripts + "/" + id + ".sh"

            package_fname = self.conf_sources + "/" + step.package.file
            # param = tar_param(step.package.file)

            with open(fname, "wb") as fp:
                fp.write(script.encode("utf-8"))

            mf_trunk = \
                "{flags}/build-{id}: {package}\n\t" + \
                "\n\t".join([
                    "mkdir -p '{sources}/build'",
                    "tar -xf '{package}' -C '{sources}/build'",
                    "cd '{sources}'/build/* && {header} bash {script}",
                    "rm -r '{sources}/build'",
                    "touch '{flags}/build-{id}'"
                ])

            mf_trunk = mf_trunk.format(
                sources = self.conf_sources,
                package = package_fname, id = id,
                script = fname,
                header = self.gen_env_header(),
                flags = self.conf_work_flags)

            makefile.append(mf_trunk)

        print("\n\n".join(makefile))
