import hashlib

def md5sum(path):
    md5 = hashlib.md5()
    
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(4096), b""):
            md5.update(chunk)

    return md5.hexdigest()

def md5str(str):
    md5 = hashlib.md5()
    md5.update(str.encode("utf-8"))
    return md5.hexdigest()
