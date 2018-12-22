# parse lfs xml source

import re
import os

from wget import wget
from lxml import etree
from md5sum import md5sum
from md5sum import md5str

PATH_PACKAGES = "/chapter03/packages.xml"
PATH_PATCHES = "/chapter03/patches.xml"

PATH_TOOLCHAIN = "/chapter05"
PATH_TOOLCHAIN_MAIN = "/chapter05/chapter05.xml"

PATH_SYSTEM = "/chapter06"
PATH_SYSTEM_MAIN = "/chapter06/chapter06.xml"

PATH_GENERAL = "/general.ent"

class Package:
    def __init__(self, name, version, url, md5, rev):
        self.name = name
        self.version = version
        self.url = url
        self.file = os.path.basename(url)
        self.rev = rev # usually None, "systemd", or "sysv"
        self.md5 = md5

    def __str__(self):
        return "<package '{}' ({}) at {} ({}), md5 {}>".format(self.name, self.version, self.url, self.file, self.md5)

    def __repr__(self):
        return self.__str__()

    def save_to(self, path, mirror_prefix = None):
        fname = path + "/" + self.file

        if os.path.exists(fname):
            if md5sum(fname) == self.md5:
                # file already exists and checksum matches
                print(fname + " " + self.md5 + " exists, skipping")
                return True
            else:
                raise Exception("{} exists but checksum does not match {}".format(fname, self.md5))

        while 1:
            # ues mirror if specified
            url = self.url if mirror_prefix is None else mirror_prefix + self.file

            try:
                suc = wget(url, path, retry = 5, timeout = 5)
            except KeyboardInterrupt:
                os.unlink(fname)
                return False

            if suc:
                if md5sum(fname) == self.md5:
                    return True
                else:
                    print("md5 not match, retrying")
                    continue # md5 not match
            else:
                os.unlink(fname)
                return False

class Patch(Package):
    def __str__(self):
        return "<patch '{}' at {} ({})>".format(self.name, self.url, self.file)

class Step():
    def __init__(self, name, package, scripts):
        self.name = name
        self.package = package
        self.scripts = scripts

    def __str__(self):
        return "<step '{}' with {}, {} command(s)>".format(self.name, self.package, len(self.scripts))

    def __repr__(self):
        return self.__str__()

    # step id
    # consistent across different runs
    def id(self):
        md5 = md5str(self.gen_build_script())
        canon_name = self.name.replace(" ", "_") + "-" + md5 
        return canon_name

    def gen_build_script(self):
        script = """#!/bin/bash

set +h
set -e
umask 022

""" + "\n".join(map(lambda c: c.cmd, self.scripts)) + "\n"

        return script

class Command():
    def __init__(self, cmd, type):
        self.cmd = cmd
        self.type = type

    def __str__(self):
        return "<cmd {} {}>".format(self.type, self.cmd)

    def __repr__(self):
        return self.__str__()

class Book:
    def __init__(self, path):
        self.path = path

        self.init_book()
        self.init_package()
        
        self.toolchain_steps = self.init_steps(PATH_TOOLCHAIN, PATH_TOOLCHAIN_MAIN)
        self.system_steps = self.init_steps(PATH_SYSTEM, PATH_SYSTEM_MAIN)

    # load basic info
    def init_book(self):
        dtd = etree.DTD(self.path + PATH_GENERAL)

        for ent in dtd.entities():
            if ent.name == "version":
                self.version = ent.content
                break   
        else:
            raise Exception("failed to find version")

    @staticmethod
    def parse_download_entry(entry):
        match = re.match(r"([^(]+)\s?(\(([^)]+)\))?\s?-", entry)

        if not match:
            raise Exception("failed to parse download entry")

        return match.group(1).strip(), match.group(3)

    # parse all required packages
    def init_package(self):
        packages = []
        patches = []

        # packages
        for entry in etree.parse(self.path + PATH_PACKAGES).findall(".//varlistentry"):
            rev = entry.get("revision")
            name, version = Book.parse_download_entry(entry.find("term").text)
            url = entry.xpath(".//para[starts-with(text(), 'Download')]")[0].find("ulink").get("url")
            md5 = entry.xpath(".//para[starts-with(text(), 'MD5 sum')]")[0].find("literal").text

            packages.append(Package(name, version, url, md5, rev))

        # patches
        for entry in etree.parse(self.path + PATH_PATCHES).findall(".//varlistentry"):
            rev = entry.get("revision")
            name, version = Book.parse_download_entry(entry.find("term").text)
            url = entry.xpath(".//para[starts-with(text(), 'Download')]")[0].find("ulink").get("url")
            md5 = entry.xpath(".//para[starts-with(text(), 'MD5 sum')]")[0].find("literal").text

            patches.append(Patch(name, version, url, md5, rev))

        self.packages = packages
        self.patches = patches

        # print(*packages, sep = "\n")
        # print(*patches, sep = "\n")

    def find_package_by_url(self, url):
        for p in self.packages:
            if p.url == url:
                return p

    # parse steps
    def init_steps(self, chap, main):
        parser = etree.XMLParser(recover = True)
        doc = etree.parse(self.path + main, parser).getroot()

        steps = []

        for include in doc.xpath("//xi:include", namespaces = { "xi": "http://www.w3.org/2001/XInclude" }):
            src = self.path + chap + "/" + include.get("href")
            xml = etree.parse(src, parser)

            info = xml.find("sect1info")

            if info is not None:
                name = xml.find("title").text
                pname = xml.find("sect1info/productname").text
                url = xml.find("sect1info/address").text
                package = self.find_package_by_url(url)

                if not package:
                    raise Exception("unregistered package " + pname)

                scripts = [ Command(cmd.text, cmd.get("remap")) for cmd in xml.findall("//screen/userinput") ]

                steps.append(Step(name, package, scripts))

        # print(*steps, sep = "\n")

        return steps
