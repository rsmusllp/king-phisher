FROM debian
LABEL maintainer "Alex Cline <alex.cline@gmail.com>"

RUN apt-get update && apt-get install -y \
	build-essential \
	libssl-dev \
	libffi-dev \
	python-dev \
	dirmngr \
	gnupg \
	libgl1-mesa-dri \
	libgl1-mesa-glx \
	git \
	ca-certificates \
	--no-install-recommends \
	&& rm -rf /var/lib/apt/lists/*

WORKDIR /opt
RUN git clone https://github.com/securestate/king-phisher.git

WORKDIR /opt/king-phisher
RUN tools/install.sh --skip-server

ENTRYPOINT ["/opt/king-phisher/KingPhisher"]