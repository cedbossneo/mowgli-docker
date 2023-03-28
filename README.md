# Mowgli in Docker

This container runs OpenMower Mowgli software remotely.

## Setup

### Mower PI

Be sure you don't run ROS along with ser2net in order to avoid conflicts

```bash
apt-get install -y ser2net
systemctl enable ser2net
```

Edit /etc/ser2net.conf and add theses lines on the bottom, change devices according to your setup

```
# Mowgli
4001:raw:600:/dev/ttyACM0:115200
# GPS
4002:raw:600:/dev/ttyACM1:115200
# IMU
4003:raw:600:/dev/ttyAMA0:9600
```

Finally

```bash
systemctl start ser2net
```

### Remote Machine

- Clone this repository somewhere on your system.
- Install Docker ( curl -sSL https://get.docker.com | sh )
- Edit your Mowgli config in the config directory
- Put your map in the ros directory.

Finally, launch:

```bash
MOWER_IP=your_mower_ip docker-compose up
```

or, if you want to have it in deamon mode

```bash
MOWER_IP=your_mower_ip docker-compose up -d
```

That's it !

## Usage

### Buttons

You can use the scripts in buttons directory to press home / start

### Logs

```bash
docker-compose logs -f mowgli
```

### RViz

ROS Ports are exposed to the host machine so you can easily access RViz by setting your ROS_MASTER_IP to the machine where your docker container runs.

### Shutdown

```bash
docker-compose stop
```
