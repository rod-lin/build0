#!/usr/bin/env python3

import book
import toml
import builder

if __name__ == "__main__":
    with open("config.toml") as fp:
        builder = builder.Builder(toml.loads(fp.read()))
        builder.init_root()
        builder.download_sources()
        builder.gen_toolchain_makefile()
