FROM securestate/king-phisher-server
MAINTAINER Devin Shimola <dshimola@securestate.com>
RUN PASSWORD=`cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 16 | head -n 1`; useradd kingphisher -m -s /usr/sbin/nologin; echo "kingphisher:$PASSWORD" | chpasswd; echo "****************************************\nDO NOT LOSE THIS\nPassword for kingphisher is $PASSWORD\n****************************************";
CMD [ "/bin/bash", "/config/startup.sh" ]

