#!/usr/bin/env python3
"""Run the PSA Cryto API compliance test suite.
Clone the repo and check out the commit specified by PSA_ARCH_TEST_REPO and PSA_ARCH_TEST_REF,
then complie and run the test suite.
Known defects in either the test suite or mbedtls - identified by their test number - are ignored,
while unexpected failures AND successes are reported as errors,
to help keep the list of known defects as up to date as possible.
"""
import os
import re
import shutil
import subprocess
import sys

EXPECTED_FAILURES = {
    216, 221, 224, 225, 248, 249, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263
}
PSA_ARCH_TESTS_REPO = 'https://github.com/ronald-cron-arm/psa-arch-tests.git'
PSA_ARCH_TESTS_REF = 'crypto1.0-3.0'

#pylint: disable=too-many-branches,too-many-statements
def main():
    mbedtls_dir = os.getcwd()

    if not os.path.exists('library/libmbedcrypto.a'):
        subprocess.check_call(['make', '-C', 'library', 'libmbedcrypto.a'])

    psa_arch_tests_dir = 'psa-arch-tests'
    try:
        os.mkdir(psa_arch_tests_dir)
    except FileExistsError:
        pass
    try:
        os.chdir(psa_arch_tests_dir)

        subprocess.check_call(['git', 'init'])
        subprocess.check_call(['git', 'fetch', PSA_ARCH_TESTS_REPO, PSA_ARCH_TESTS_REF])
        subprocess.check_call(['git', 'checkout', 'FETCH_HEAD'])

        build_dir = 'api-tests/build'
        try:
            shutil.rmtree(build_dir)
        except FileNotFoundError:
            pass
        os.mkdir(build_dir)
        os.chdir(build_dir)

        #pylint: disable=bad-continuation
        subprocess.check_call([
            'cmake', '..',
                     '-GUnix Makefiles',
                     '-DTARGET=tgt_dev_apis_stdc',
                     '-DTOOLCHAIN=HOST_GCC',
                     '-DSUITE=CRYPTO',
                     '-DPSA_CRYPTO_LIB_FILENAME={}/library/libmbedcrypto.a'.format(mbedtls_dir),
                     '-DPSA_INCLUDE_PATHS={}/include'.format(mbedtls_dir)
        ])
        subprocess.check_call(['cmake', '--build', '.'])

        proc = subprocess.Popen(['./psa-arch-tests-crypto'],
                                bufsize=1, stdout=subprocess.PIPE, universal_newlines=True)

        test_re = re.compile(
            '^TEST: (?P<test_num>[0-9]*)|'
            '^TEST RESULT: (?P<test_result>FAILED|PASSED)'
        )
        test = -1
        unexpected_successes = set(EXPECTED_FAILURES)
        expected_failures = []
        unexpected_failures = []
        for line in proc.stdout:
            print(line, end='')
            match = test_re.match(line)
            if match is not None:
                groupdict = match.groupdict()
                test_num = groupdict['test_num']
                if test_num is not None:
                    test = int(test_num)
                elif groupdict['test_result'] == 'FAILED':
                    try:
                        unexpected_successes.remove(test)
                        expected_failures.append(test)
                        print('Expected failure, ignoring')
                    except KeyError:
                        unexpected_failures.append(test)
                        print('ERROR: Unexpected failure')
                elif test in unexpected_successes:
                    print('ERROR: Unexpected success')
        proc.wait()

        print()
        print('***** test_psa_compliance.py report ******')
        print()
        print('Expected failures:', ', '.join(str(i) for i in expected_failures))
        print('Unexpected failures:', ', '.join(str(i) for i in unexpected_failures))
        print('Unexpected successes:', ', '.join(str(i) for i in sorted(unexpected_successes)))
        print()
        if unexpected_successes or unexpected_failures:
            if unexpected_successes:
                print('Unexpected successes encountered.')
                print('Please remove the corresponding tests from '
                      'EXPECTED_FAILURES in tests/scripts/compliance_test.py')
                print()
            print('FAILED')
            return 1
        else:
            shutil.rmtree(psa_arch_tests_dir)
            print('SUCCESS')
            return 0
    finally:
        os.chdir(mbedtls_dir)

if __name__ == '__main__':
    sys.exit(main())
