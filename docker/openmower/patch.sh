#!/bin/bash
set -xe
echo "Patching for implausible wheel ticks"


FILE="/opt/open_mower_ros/src/lib/xbot_positioning/src/xbot_positioning.cpp"
# Define the line after which the new code should be inserted
LINE="vx = d_ticks / dt;"

# Define the code to be inserted
NEW_CODE='    // Ignore implausible wheel tick calculation
    if(abs(vx) > 0.6) {
        ROS_WARN_STREAM("got vx > 0.6 (" << vx << ") - dropping measurement");
        vx = 0.0;
        return;
    }'

# Check if the NEW_CODE is already present in the file
if ! grep -q "ROS_WARN_STREAM(\"got vx > 0.6 (\" << vx << \") - dropping measurement\");" "$FILE"; then
    # Use awk to insert the new code after the specified line
    awk -v new_code="$NEW_CODE" -v line="$LINE" '
    $0 ~ line {
        print $0
        print new_code
        next
    }
    { print }
    ' "$FILE" > temp_file && mv temp_file "$FILE"
else
    echo "The new code is already present in the file. Skipping insertion."
fi
