import os
import os.path
import platform
import re
import runpy
import subprocess
import sys
import time
import traceback
from os.path import join
from subprocess import PIPE, CalledProcessError, Popen


class MakeCertPem:
    """ create openssl cert bundle from system certificates """

    def __init__(self, openssl):
        self.openssl = openssl

    def is_valid_cert(self, cert):
        """ check if cert is valid according to openssl"""
        cmd = [self.openssl, "x509", "-inform", "pem", "-checkend", "0", "-noout"]
        # print("D: is_valid_cert %r" % cmd)
        proc = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate(cert)
        # print("out: %s; err:%s; ret:%i" % (stdout, stderr, proc.returncode))
        return proc.returncode == 0

    def get_certs(self):
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
                           if self.is_valid_cert(cert)]
            print("I: of which %i are valid certificates" % len(valid_certs))
            return valid_certs
        except OSError:
            print("E: extracting certificates using %r" % cmd)
            traceback.print_exc()
        except CalledProcessError as err:
            print(("E: extracting certificates using %r, exit=%i" %
                  (cmd, err.returncode)))

    @staticmethod
    def write_certs(certs, dest):
        """ write concatenated certs to dest """
        with open(dest, "wb") as output:
            output.write(b"\n".join(certs))

    def regen(self, dest):
        """ main program """
        print("I: make_cert_pem %s %s" % (self.openssl, dest))
        certs = self.get_certs()
        if certs is None:
            print("E: no certificate extracted")
            return -1
        else:
            self.write_certs(certs, dest)
            print("I: updated %s with %i certificates" % (dest, len(certs)))
            return 0


# print("launcher.py sys.argv=", sys.argv)
bundlepath = sys.argv.pop(0)
app = os.path.basename(sys.argv[0])

bundle_contents = join(bundlepath, 'Contents')
bundle_res = join(bundle_contents, 'Resources')

bundle_lib = join(bundle_res, 'lib')
bundle_bin = join(bundle_res, 'bin')
bundle_data = join(bundle_res, 'share')
bundle_etc = join(bundle_res, 'etc')

os.environ['CHARSETALIASDIR'] = bundle_lib
os.environ['DYLD_LIBRARY_PATH'] = bundle_lib
os.environ['GTK_DATA_PREFIX'] = bundle_res
os.environ['GTK_EXE_PREFIX'] = bundle_res
os.environ['GTK_PATH'] = bundle_res
os.environ['LD_LIBRARY_PATH'] = bundle_lib
os.environ['XDG_CONFIG_DIRS'] = bundle_etc
os.environ['XDG_DATA_DIRS'] = bundle_data

os.environ['PANGO_LIBDIR'] = bundle_lib
os.environ['PANGO_RC_FILE'] = join(bundle_etc, 'pango', 'pangorc')
os.environ['PANGO_SYSCONFDIR'] = bundle_etc
os.environ['GDK_PIXBUF_MODULE_FILE'] = join(bundle_lib, 'gdk-pixbuf-2.0',
                                            '2.10.0', 'loaders.cache')
if int(platform.release().split('.')[0]) > 10:
    os.environ['GTK_IM_MODULE_FILE'] = join(bundle_etc, 'gtk-3.0',
                                            'gtk.immodules')

os.environ['GI_TYPELIB_PATH'] = join(bundle_lib, 'girepository-1.0')

# for forked python
os.environ['PYTHONHOME'] = bundle_res
# Set $PYTHON to point inside the bundle
PYVER = 'python3.9'
sys.path.append(bundle_res)
print('System Path:\n', '\n'.join(sys.path))

# see https://gpodder.github.io/docs/user-manual.html#gpodder-home-folder-and-download-location
# To override gPodder home and/or download directory:
# 1. uncomment (remove the pound sign and space) at the beginning of the relevant line
# 2. replace ~/gPodderData or ~/gPodderDownloads with the path you want for your gPodder home
#    (you can move the original folder in the Finder first,
#     then drag and drop to the launcher.py in TextEdit to ensure the correct path is set)
# uncomment the following line to override gPodder home
# os.environ['GPODDER_HOME'] = expanduser('~/gPodderData')
# uncomment the following line to override gPodder download directory
# os.environ['GPODDER_DOWNLOAD_DIR'] = expanduser('~/gPodderDownloads')

for k, v in os.environ.items():
    print("%s=%s" % (k, v))


def gpodder_home():
    # don't inadvertently create the new gPodder home,
    # it would be preferred to the old one
    default_path = join(os.environ['HOME'], 'Library', 'Application Support', 'gPodder')
    cands = [
        os.environ.get('GPODDER_HOME'),
        default_path,
        join(os.environ['HOME'], 'gPodder'),
    ]
    for cand in cands:
        if cand and os.path.exists(cand):
            return cand
    return default_path


gphome = gpodder_home()
os.makedirs(join(gphome, 'openssl'), exist_ok=True)
# generate cert.extracted.pem
cert_gen = join(gphome, 'openssl', 'cert.extracted.pem')
cert_pem = join(gphome, 'openssl', 'cert.pem')
regen = False
if not os.path.isfile(cert_gen):
    regen = True
else:
    last_modified = os.stat(cert_gen).st_mtime
    regen = last_modified < time.time() - 3600 * 7

if regen:
    print('(Re)generating', cert_pem)
    openssl = join(bundle_bin, 'openssl')
    MakeCertPem(openssl).regen(cert_gen)
else:
    print('No regenerating', cert_gen, 'it\'s fresh enough')

# and link to it by default. Users may want to point cert.pem to MacPorts
# /opt/local/etc/openssl/cert.pem, for instance.
if not os.path.exists(cert_pem):
    os.symlink(os.path.basename(cert_gen), cert_pem)
# Set path to CA files
os.environ['SSL_CERT_FILE'] = cert_pem

if app == 'run-python':
    python_exe = join(bundle_contents, 'MacOS', 'python3')
    # executable is repeated as argv[0].
    # Old sys.argv[0] points to Contents/MacOS so must be removed
    args = [python_exe] + sys.argv[1:]
    # print("running", args)
    os.execv(python_exe, args)
elif app == 'run-pip':
    python_exe = join(bundle_contents, 'MacOS', 'python3')
    pip = join(bundle_contents, 'Resources', 'bin', 'pip3')
    # executable is repeated as argv[0].
    # Old sys.argv[0] points to Contents/MacOS so must be removed
    args = [python_exe, pip] + sys.argv[1:]
    # print("running", args)
    os.execv(python_exe, args)
else:
    import runpy
    runpy.run_path(join(bundle_bin, app), run_name='__main__')
