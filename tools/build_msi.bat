@ECHO off
python tools\cx_freeze.py build
python tools\cx_freeze.py bdist_msi
