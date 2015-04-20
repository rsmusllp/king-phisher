FROM securestate/king-phisher-server
MAINTAINER Devin Shimola <dshimola@securestate.com>
RUN PASSWORD=`cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 14 | head -n 1`; useradd kingphisher -m -s /bin/bash; echo "kingphisher:$PASSWORD" | chpasswd; echo "password is $PASSWORD";
CMD [ "/bin/bash", "/config/startup.sh" ]

