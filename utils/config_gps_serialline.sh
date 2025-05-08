# configure serial GPS to avoid sending data
stty -F /dev/gps 460800 raw -echo -echoe -echok
