# Install ![GitHub Downloads][downloads-status]
The King Phisher client is supported on Windows and Linux, while the King Phisher
server is only supported on Linux.

## Linux (Client & Server)
For installation on [supported Linux][operating-systems] distros:

```bash
wget -q https://github.com/securestate/king-phisher/raw/master/tools/install.sh && \
sudo bash ./install.sh
```
## Windows (Client Only)
Download the latest [Windows build here.][releases]

## Windows 10 Subsystem
- Download [VcXsrv][vcxsrv] from the Microsoft Store
- Clone King-Phisher repo and install as normal
- include in your .bashrc/.zshrc file ```export DISPLAY=:0.0```

## Getting Started
- [Getting Started][wiki-getting-started]
- [How to videos][videos]
- [Wiki][wiki]

[downloads-status]: https://img.shields.io/github/downloads/securestate/king-phisher/total.svg?style=flat-square
[operating-systems]: https://github.com/securestate/king-phisher/wiki/Advanced-Installation#install-script-supported-flavors
[releases]: https://github.com/securestate/king-phisher/releases
[videos]: https://securestate.wistia.com/projects/laevqz2p29
[wiki]: https://github.com/securestate/king-phisher/wiki
[wiki-getting-started]: https://github.com/securestate/king-phisher/wiki/Getting-Started
[vcxsrv]: https://sourceforge.net/projects/vcxsrv/
