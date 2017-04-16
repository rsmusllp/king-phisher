# King-Phisher Client on Mac

The only two requirements for running the King-Phisher client on a Mac are [Docker for Mac](https://docs.docker.com/docker-for-mac/install/#download-docker-for-mac) and [XQuartz](https://www.xquartz.org/). Docker for Mac runs the Linux container the King-Phisher client is installed into, and XQuartz which provides the X11 display for the King-Phisher client to render to.

## Install and configure XQuartz

1. Install XQuartz for Mac:
    `brew install cask xquartz` or https://www.xquartz.org/
2. Start xquartz from Applications > Utilities
3. Configure network connections so docker containers can connect to the X11 server
    XQuartz Menu > Preferences > Security > [✓] Allow connections from network clients

## Install Docker for Mac

1. Install docker for Mac:
    https://docs.docker.com/docker-for-mac/install/#download-docker-for-mac

## Build and run king-phisher docker container
In Terminal.app, run
1. Whitelist your machine's IP address to connect to the X11 server
    ```
    ip=$(ifconfig en0 | grep inet | awk '$1=="inet" {print $2}')
    xhost + $ip
    ```
2. Build the docker image. This will probably take 20+ minutes
    ```
    docker build -t king-phisher .
    ```
3. Run the docker container. The mounted volumes are for connecting to the X11 display and saving the King-Phisher preferences to your home directory.
    ```
    docker run -d -e DISPLAY=$ip:0 -v /tmp/.X11-unix:/tmp/.X11-unix -v ~/.config:/root/.config king-phisher
    ```

_Note: You can remove the `-d` from the docker command above to see King-Phisher logs for troubleshooting._