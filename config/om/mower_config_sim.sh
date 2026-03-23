################################
## Simulation Config          ##
## No real hardware needed    ##
################################

export OM_NO_COMMS=true
export OM_NO_GPS=true
export OM_MOWER="CUSTOM"
export OM_HARDWARE_VERSION=""
export OM_MOWER_ESC_TYPE="xesc_mini"
export OM_MOWER_GAMEPAD="xbox360"

################################
##   GPS Settings (sim)       ##
################################
export OM_USE_RELATIVE_POSITION=False
export OM_DATUM_LAT=48.8566
export OM_DATUM_LONG=2.3522
export OM_GPS_PROTOCOL=UBX
export OM_USE_NTRIP=False
export OM_NTRIP_HOSTNAME=localhost
export OM_NTRIP_PORT=2101
export OM_NTRIP_USER=sim
export OM_NTRIP_PASSWORD=sim
export OM_NTRIP_ENDPOINT=SIM
export OM_USE_F9R_SENSOR_FUSION=False

export OM_GPS_WAIT_TIME_SEC=2.0
export OM_GPS_TIMEOUT_SEC=10.0
export OM_GPS_PORT=/dev/null
export OM_GPS_BAUDRATE=115200

################################
##    Mower Logic (sim)       ##
################################
export OM_DOCKING_DISTANCE=1.0
export OM_UNDOCK_DISTANCE=1.0
export OM_OUTLINE_COUNT=4
export OM_TOOL_WIDTH=0.13
export OM_BATTERY_CRITICAL_VOLTAGE=22.0
export OM_BATTERY_EMPTY_VOLTAGE=23.0
export OM_BATTERY_FULL_VOLTAGE=28.0
export OM_MOWING_MOTOR_TEMP_HIGH=80.0
export OM_MOWING_MOTOR_TEMP_LOW=40.0
export OM_ENABLE_MOWER=false
export OM_AUTOMATIC_MODE=0
export OM_OUTLINE_OFFSET=0.05
# In sim, GPS is published at base_link (robot center), not at antenna
export OM_ANTENNA_OFFSET_X=0.0
export OM_ANTENNA_OFFSET_Y=0.0
export OM_WHEEL_DISTANCE_M=0.325
export OM_WHEEL_TICKS_PER_M=300.0
# Disabled in sim - heatmap_generator crashes without proper sensor setup
#export OM_HEATMAP_SENSOR_IDS=om_gps_accuracy
