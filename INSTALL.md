# Install ![GitHub Downloads][downloads-status]
The King Phisher client is supported on Windows and Linux, while the King Phisher
server is only supported on Linux.

## Linux (Client & Server)
For installation on [supported Linux][operating-systems] distros:

```bash
wget -q https://github.com/securestate/king-phisher/raw/master/tools/install.sh && \
sudo bash ./install.sh
```

This process may result in errors being displayed. In this case, allow
the installation process to continue as it will attempt to address as
many of them as it can.

## Windows (Client Only)
Download the latest [Windows build here.][releases]

### Windows 10 Subsystem For Linux (WSL)
This is recommend for windows users as this will provide faster performance and 
more features.

- Enable [WSL][wsl]
  - When choosing your linux distro select Ubuntu 18.04 or Kali
- Download and install a X Window System Server. The two below are the most popular
  - [Xming][xming]
  - [VcXsrv][vcxsrv]
- From powershell run `bash` to get your linux terminal
- run `echo "export DISPLAY=127.0.0.1:0.0" >> ~/.bashrc`
- Install King Phisher with the commands from the Linux (Client & Server) section above
- Change working directory to King Phisher and start client
  - `cd /opt/king-phisher`
  - `./KingPhisher`

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
[wsl]: https://docs.microsoft.com/en-us/windows/wsl/install-win10
[vcxsrv]: https://sourceforge.net/projects/vcxsrv/
[xming]: https://sourceforge.net/projects/xming/
