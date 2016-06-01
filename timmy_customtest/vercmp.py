import re


def rpm_vercmp(a, b):
    '''Implementation of RPM's rpmvercmp function
    http://rpm.org/wiki/PackagerDocs/Dependencies
    http://rpm.org/gitweb?p=rpm.git;a=blob;f=lib/rpmvercmp.c'''
    a_newer = 1
    b_newer = -1
    equal = 0
    if a == b:
        return equal
    if a and not b:
        return a_newer
    if b and not a:
        return b_newer
    a_epoch = re.match('^(-?\d):', a)
    b_epoch = re.match('^(-?\d):', b)
    if a_epoch:
        if b_epoch:
            if int(a_epoch.groups()[0]) > int(b_epoch.groups()[0]):
                return a_newer
            if int(a_epoch.groups()[0]) < int(b_epoch.groups()[0]):
                return b_newer
        else:
            if int(a_epoch.groups()[0]) > 0:
                return a_newer
            if int(a_epoch.groups()[0]) < 0:
                return b_newer
    elif b_epoch:
        if int(b_epoch.groups()[0]) > 0:
            return b_newer
        if int(b_epoch.groups()[0]) < 0:
            return a_newer
    a_list = re.findall('[a-zA-Z]+|[0-9]+|~', a)
    b_list = re.findall('[a-zA-Z]+|[0-9]+|~', b)
    for index, value in enumerate(a_list):
        if index >= len(b_list):
            if value == '~':
                return b_newer
            else:
                return a_newer
        elif value == '~':
            if b_list[index] != '~':
                return b_newer
            else:
                continue
        elif b_list[index] == '~':
            return a_newer
        else:
            if value.isdigit():
                if not b_list[index].isdigit():
                    return a_newer
                else:
                    if int(value) > int(b_list[index]):
                        return a_newer
                    if int(value) < int(b_list[index]):
                        return b_newer
            else:
                if b_list[index].isdigit():
                    return b_newer
                else:
                    if value > b_list[index]:
                        return a_newer
                    if value < b_list[index]:
                        return b_newer
    if len(b_list) > len(a_list):
        if b_list[len(a_list)] == '~':
            return a_newer
        else:
            return b_newer
    return equal


def deb_vercmp(a, b):
    '''Implementation of Debian version comparison.
    https://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-Version
    http://dpkg.sourcearchive.com/documentation/1.15.6/vercmp_8c-source.html
    '''
    def cmp(a, b):

        def order(x):
            if x == '~':
                return -1
            if x.isdigit():
                return int(x)
            if ord(x) in range(ord('A'), ord('Z')+1)+range(ord('a'), ord('z')):
                return x
            else:
                return ord(x) + 256

        def check_alpha(a, ia):
            return ia < len(a) and not a[ia].isdigit()

        def check_digit(a, ia):
            return ia < len(a) and a[ia].isdigit()

        ia = 0
        ib = 0
        iter = -1
        while ia < len(a) or ib < len(b):
            iter += 1
            diff = 0
            '''Workaround for end of string:
            add 0 to compare lower then everything except '~'.
            It is impossible that both ia and ib get over string bounds, so
            an endless loop cannot happen.
            '''
            if ia == len(a):
                a += '0'
            if ib == len(b):
                b += '0'
            while check_alpha(a, ia) or check_alpha(b, ib):
                if order(a[ia]) > order(b[ib]):
                    return 1
                if order(a[ia]) < order(b[ib]):
                    return -1
                ia += 1
                ib += 1
            while ia < len(a) and a[ia] == '0':
                ia += 1
            while ib < len(b) and b[ib] == '0':
                ib += 1
            while check_digit(a, ia) and check_digit(b, ib):
                if not diff:
                    diff = int(a[ia]) - int(b[ib])
                ia += 1
                ib += 1
            if ia < len(a) and a[ia].isdigit():
                return 1
            if ib < len(b) and b[ib].isdigit():
                return -1
            if diff:
                return diff
        return 0

    a_newer = 1
    b_newer = -1
    equal = 0
    if a == b:
        return equal
    if a and not b:
        return a_newer
    if b and not a:
        return b_newer
    a_epoch = re.match('^(\d):', a)
    b_epoch = re.match('^(\d):', b)
    if a_epoch:
        if b_epoch:
            if int(a_epoch.groups()[0]) > int(b_epoch.groups()[0]):
                return a_newer
            if int(a_epoch.groups()[0]) < int(b_epoch.groups()[0]):
                return b_newer
        elif int(a_epoch.groups()[0]) > 0:
            return a_newer
        a = a[2:]
        b = b[2:]
    elif b_epoch:
        if int(b_epoch.groups()[0]) > 0:
            return b_newer
        b = b[2:]

    a_parts = re.match('^([^-].+?)?(?:-([^-]+))?$', a)
    a_version = a_revision = None
    if a_parts:
        a_version, a_revision = a_parts.groups()
    b_parts = re.match('^([^-].+?)?(?:-([^-]+))?$', b)
    b_version = b_revision = None
    if b_parts:
        b_version, b_revision = b_parts.groups()
    if a_version and not b_version:
        return a_newer
    if b_version and not a_version:
        return b_newer
    vc = cmp(a_version, b_version)
    if vc > 0:
        return a_newer
    if vc < 0:
        return b_newer
    if a_revision and not b_revision:
        return a_newer
    if b_revision and not a_revision:
        return b_newer
    rc = cmp(a_revision, b_revision)
    if rc > 0:
        return a_newer
    if rc < 0:
        return b_newer
    return equal


def vercmp(os, a, b):
    if os == 'centos':
        return rpm_vercmp(a, b)
    if os == 'ubuntu':
        return deb_vercmp(a, b)
