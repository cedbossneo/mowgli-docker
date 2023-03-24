################################
## Hardware Specific Settings ##
################################

# The type of mower you're using, not currently used but we might load a default config depending on this at some point
export OM_MOWER="YardForce500-Mowgli"

################################
##     Mowgli Settings        ##
################################
export MOWGLI_GPS_ANTENNA_OFFSET=0.36
export MOWGLI_IMU_OFFSET=0.0
export MOWGLI_DATUM_LAT=48.8831951
export MOWGLI_DATUM_LONG=2.1661984
export MOWGLI_GPS_FILTER_FACTOR=1.0
export MOWGLI_MAX_DISTANCE_TO_LAST_GPS_POS=0.10
export MOWGLI_GPSRTK_FIX_REQUIRED=false
# DR settings
export MOWGLI_DR_MAX_DURATION_SEC=20
export MOWGLI_DR_UPDATE_INTERVAL=1.0

################################
##     NTRIP Settings         ##
################################
export OM_NTRIP_HOSTNAME=caster.centipede.fr
export OM_NTRIP_PORT=2101
export OM_NTRIP_USER=centipede
export OM_NTRIP_PASSWORD=centipede
export OM_NTRIP_ENDPOINT=OUIL
export OM_GPS_SERIAL_PORT=gps

################################
##    OM MowerLogic Settings  ##
################################
# Voltages for battery to be considered full or empty
export OM_BATTERY_EMPTY_VOLTAGE=23.0
export OM_BATTERY_FULL_VOLTAGE=28.0

# GPS timeouts
export OM_GPS_WAIT_TIME_SEC=10.0
export OM_GPS_TIMEOUT_SEC=3.0

# Mowing Behavior Settings (needs to be true to enable Blade Motor)
export OM_ENABLE_MOWER=true

# Ignore GPS errors (we handle that in mowgli_proxy)
export OM_IGNORE_GPS_ERRORS=true

# Mow/Docking settings
export OM_AUTOMATIC_START=false
export OM_OUTLINE_OFFSET=0.5
export OM_OUTLINE_COUNT=1
export OM_TOOL_WIDTH=0.15
export OM_DOCKING_DISTANCE=0.85
export OM_UNDOCK_DISTANCE=1.0