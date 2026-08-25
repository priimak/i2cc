# Installation

_I2C Commander_ application is written in pure python 3.13 and can be installed on Windows, Mac or Linux. Snippets below address 
Windows installation.

Open PowerShell window and install `uv` (application for managing python and python based applications). You can skip 
this step if `uv` is already installed.

```commandline
winget install --id=astral-sh.uv  -e
```

Once `uv` is installed run

```commandline
uv tool install --cache-dir .cache -p 3.13 --force git+https://github.com/priimak/i2cc.git@release
```

This will install latest release version of _I2C Commander_ (executable i2cc.exe).

If newer version of I2C Commander is available then you can upgrade your previously installed version by running following command in PowerShell window.

```commandline
uv tool upgrade i2cc
```

To run _I2C Commander_ simply open PowerShell window type `i2cc` and press `Enter`.