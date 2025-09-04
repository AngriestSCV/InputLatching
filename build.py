#!/usr/bin/env python

import subprocess
import shutil

if __name__ == "__main__":
    try:
        shutil.rmtree("dist")
    except:
        pass
    cmd = ["pyinstaller", "InputLatching.py", ]
    cmd += [ "--add-data", "main.qml:." ]

    print(cmd)

    subprocess.run(cmd)