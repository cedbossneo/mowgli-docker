# Mowgli in Docker

This container runs OpenMower Mowgli software locally or remotely.

## Local

### Setup

Install docker with this command :

```bash
curl https://get.docker.com | sh
```

Clone this repository

```bash
git clone https://github.com/cedbossneo/mowgli-docker
```

The script suppose that your mowgli device is on /dev/mowgli and your gps on /dev/gps

WARNING: This branch works only with the new Mowgli firmware https://github.com/cedbossneo/Mowgli that allows Mowgli to runs with vanilla OpenMower without mowgli_proxy or mowgli_blade.

Finally:

```bash
docker-compose up -d
```

The OpenMower web app is hosted on port 4005 of your PI.

## Remote BY Serial Redirection

### Setup

#### Mower PI

Be sure you don't run ROS along with ser2net in order to avoid conflicts

```bash
apt-get install -y ser2net
systemctl enable ser2net
```

Create a file in udev config (/etc/udev/rules.d/50-mowgli.rules) with this content :

```
SUBSYSTEM=="tty" ATTRS{product}=="Mowgli", SYMLINK+="mowgli"
SUBSYSTEM=="tty" ATTRS{idVendor}=="1546" ATTRS{idProduct}=="01a9", SYMLINK+="gps"
KERNEL=="ttyACM[0-9]*",MODE="0777"
```

Edit /etc/ser2net.conf and add theses lines on the bottom, change devices according to your setup

```
# Mowgli
4001:raw:600:/dev/mowgli:115200 NONE 1STOPBIT 8DATABITS -RTSCTS
# GPS
4002:raw:600:/dev/gps:115200 NONE 1STOPBIT 8DATABITS -RTSCTS
```

Finally reboot your PI

#### Remote Machine

- Clone this repository somewhere on your system.
- Install Docker ( curl -sSL https://get.docker.com | sh )
- Edit your Mowgli config in the config directory
- Put your map in the ros directory.

Finally, launch:

```bash
MOWER_IP=your_mower_ip docker-compose -f docker-compose.ser2net.yaml up
```

or, if you want to have it in deamon mode

```bash
MOWER_IP=your_mower_ip docker-compose -f docker-compose.ser2net.yaml up -d
```

That's it !

## Remote BY Splitting OpenMower and ROSSERIAL

### Setup

#### Remote Host

Install docker with this command :

```bash
curl https://get.docker.com | sh
```

Clone this repository

```bash
git clone https://github.com/cedbossneo/mowgli-docker
```

The script suppose that your mowgli device is on /dev/mowgli and your gps on /dev/gps

WARNING: You must have the same mower_config on both pi and remote computer

Finally:

```bash
docker-compose -f docker-compose.remote.host.yaml up -d
```

#### Mower PI

Install docker with this command :

```bash
curl https://get.docker.com | sh
```

Clone this repository

```bash
git clone https://github.com/cedbossneo/mowgli-docker
```

The script suppose that your mowgli device is on /dev/mowgli and your gps on /dev/gps

WARNING: You must have the same mower_config on both pi and remote computer

Finally:

```bash
HOST_IP=remote_host_ip docker-compose -f docker-compose.remote.pi.yaml up -d
```

## Usage

### Buttons

You can use the scripts in buttons directory to press home / start

### Logs

```bash
docker-compose -f docker-compose.yaml logs -f openmower
```

### RViz

ROS Ports are exposed to the host machine so you can easily access RViz by setting your ROS_MASTER_IP to the machine where your docker container runs.

### Shutdown

```bash
docker-compose -f docker-compose.yaml stop
```
