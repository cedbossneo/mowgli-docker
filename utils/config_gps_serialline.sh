# configure serial GPS to avoid sending data
stty -F /dev/ttyUSB0 921600 raw -echo
