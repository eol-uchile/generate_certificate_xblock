#!/bin/dash
pip install -e /openedx/requirements/generate_certificate_xblock

cd /openedx/requirements/generate_certificate_xblock
cp /openedx/edx-platform/setup.cfg .
mkdir test_root
cd test_root/
ln -s /openedx/staticfiles .

cd /openedx/requirements/generate_certificate_xblock

DJANGO_SETTINGS_MODULE=lms.envs.test EDXAPP_TEST_MONGO_HOST=mongodb pytest generate_certificate/tests.py
