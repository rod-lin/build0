import os
import signal

# return True if success
def wget(url, dir, retry = 0, timeout = 5):
    cmd = "wget --no-check-certificate --retry-connrefused --waitretry=1 --read-timeout={} --timeout={} -t {} -P {} {}".format(timeout, timeout, retry, dir, url)
    ret = os.system(cmd)

    # exit if received SIGINT
    if os.WIFSIGNALED(ret) and os.WTERMSIG(ret) == signal.SIGINT:
        raise KeyboardInterrupt()

    return ret == 0
