# -*- coding: utf-8 -*-
""" A script to initialize our bundled openssl CA trust store
    based on your System's keychain

    Released under the same licence as gPodder (GPL3 or later)
    Copyright (c) 2016 Eric Le Lay
"""

import argparse
import re
import subprocess
import sys
import traceback
from subprocess import PIPE, CalledProcessError, Popen


def is_valid_cert(openssl, cert):
    """ check if cert is valid according to openssl"""

    cmd = [openssl, "x509", "-inform", "pem", "-checkend", "0", "-noout"]
    # print("D: is_valid_cert %r" % cmd)
    proc = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout, stderr = proc.communicate(cert)
    # print("out: %s; err:%s; ret:%i" % (stdout, stderr, proc.returncode))
    return proc.returncode == 0


def get_certs(openssl):
    """ extract System's certificates then filter them by validity
        and return a list of text of valid certs
    """

    cmd = ["security", "find-certificate", "-a", "-p",
           "/System/Library/Keychains/SystemRootCertificates.keychain"]
    cert_re = re.compile(b"^-----BEGIN CERTIFICATE-----$"
                         + b".+?"
                         + b"^-----END CERTIFICATE-----$", re.M | re.S)
    try:
        certs_str = subprocess.check_output(cmd)
        all_certs = cert_re.findall(certs_str)
        print("I: extracted %i certificates" % len(all_certs))
        valid_certs = [cert for cert in all_certs
                       if is_valid_cert(openssl, cert)]
        print("I: of which %i are valid certificates" % len(valid_certs))
        return valid_certs
    except OSError:
        print("E: extracting certificates using %r" % cmd)
        traceback.print_exc()
    except CalledProcessError as err:
        print(("E: extracting certificates using %r, exit=%i" %
              (cmd, err.returncode)))


def write_certs(certs, dest):
    """ write concatenated certs to dest """

    with open(dest, "wb") as output:
        output.write(b"\n".join(certs))


def main(openssl, dest):
    """ main program """

    print("I: make_cert_pem.py %s %s" % (openssl, dest))
    certs = get_certs(openssl)
    if certs is None:
        print("E: no certificate extracted")
        return -1
    else:
        write_certs(certs, dest)
        print("I: updated %s with %i certificates" % (dest, len(certs)))
        return 0


PARSER = argparse.ArgumentParser(
    description='Extract system certificates for openssl')
PARSER.add_argument("openssl",
                    metavar="OPENSSL_EXE",
                    help="absolute path to the openssl executable")
PARSER.add_argument("dest",
                    metavar="DEST_FILE",
                    help="absolute path to the certs.pem file to write to")

if __name__ == "__main__":

    ARGS = PARSER.parse_args()
    sys.exit(main(ARGS.openssl, ARGS.dest))
