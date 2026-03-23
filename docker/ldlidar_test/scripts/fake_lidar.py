#!/usr/bin/env python3
"""
Fake LD19 lidar publisher for offline testing.

Publishes sensor_msgs/LaserScan on /scan with:
- Configurable simulated obstacles (via FAKE_OBSTACLES env var)
- Static TF from base_link to base_laser
- Realistic LD19 specs: 360 deg, 12m range, ~10Hz

Usage:
  FAKE_OBSTACLES="1.5:0,2.0:90" means obstacles at 1.5m@0deg and 2.0m@90deg
  Each obstacle is distance_meters:angle_degrees, comma-separated.
  Without FAKE_OBSTACLES, publishes a clear scan (all max range).
"""

import os
import math
import rospy
import tf2_ros
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import TransformStamped


def parse_obstacles(env_str):
    """Parse 'dist:angle,dist:angle,...' into list of (distance, angle_rad)."""
    obstacles = []
    if not env_str:
        return obstacles
    for pair in env_str.split(","):
        pair = pair.strip()
        if ":" not in pair:
            continue
        dist_str, angle_str = pair.split(":", 1)
        dist = float(dist_str)
        angle_rad = math.radians(float(angle_str))
        obstacles.append((dist, angle_rad))
    return obstacles


def create_scan_msg(frame_id, obstacles, scan_time):
    """Create a LaserScan message mimicking the LD19 specs."""
    scan = LaserScan()
    scan.header.stamp = rospy.Time.now()
    scan.header.frame_id = frame_id

    # LD19 specs
    scan.angle_min = 0.0
    scan.angle_max = 2.0 * math.pi
    num_readings = 360
    scan.angle_increment = (scan.angle_max - scan.angle_min) / num_readings
    scan.time_increment = scan_time / num_readings
    scan.scan_time = scan_time
    scan.range_min = 0.05
    scan.range_max = 12.0

    # Default: all clear at max range
    ranges = [scan.range_max] * num_readings
    intensities = [0.0] * num_readings

    # Place obstacles as gaussian blobs (5 degree width)
    for dist, angle in obstacles:
        center_idx = int(angle / scan.angle_increment) % num_readings
        width = 5  # degrees
        for offset in range(-width, width + 1):
            idx = (center_idx + offset) % num_readings
            falloff = math.exp(-0.5 * (offset / 2.0) ** 2)
            simulated_range = dist + (1.0 - falloff) * 0.3
            if simulated_range < ranges[idx]:
                ranges[idx] = simulated_range
                intensities[idx] = 200.0 * falloff

    scan.ranges = ranges
    scan.intensities = intensities
    return scan


def publish_static_tf(frame_id):
    """Publish static TF base_link -> base_laser."""
    broadcaster = tf2_ros.StaticTransformBroadcaster()
    t = TransformStamped()
    t.header.stamp = rospy.Time.now()
    t.header.frame_id = "base_link"
    t.child_frame_id = frame_id
    t.transform.translation.x = 0.0
    t.transform.translation.y = 0.0
    t.transform.translation.z = 0.18  # LD19 mounted ~18cm above base
    t.transform.rotation.w = 1.0
    broadcaster.sendTransform(t)


def main():
    rospy.init_node("fake_lidar", anonymous=False)

    topic = os.environ.get("LIDAR_TOPIC", "/scan")
    frame_id = os.environ.get("LIDAR_FRAME_ID", "base_laser")
    rate_hz = float(os.environ.get("FAKE_LIDAR_RATE", "10"))
    obstacle_str = os.environ.get("FAKE_OBSTACLES", "")
    moving = os.environ.get("FAKE_OBSTACLES_MOVING", "false").lower() == "true"

    obstacles = parse_obstacles(obstacle_str)

    rospy.loginfo(f"Fake lidar: topic={topic}, frame={frame_id}, rate={rate_hz}Hz")
    rospy.loginfo(f"Obstacles: {obstacles if obstacles else 'none (clear scan)'}")
    rospy.loginfo(f"Moving obstacles: {moving}")

    pub = rospy.Publisher(topic, LaserScan, queue_size=10)
    publish_static_tf(frame_id)

    rate = rospy.Rate(rate_hz)
    scan_time = 1.0 / rate_hz
    t = 0.0

    while not rospy.is_shutdown():
        if moving and obstacles:
            # Move obstacles slowly in a circle
            moved = []
            for dist, base_angle in obstacles:
                angle = base_angle + 0.2 * math.sin(t * 0.5)
                d = dist + 0.3 * math.sin(t * 0.3)
                d = max(0.1, d)
                moved.append((d, angle))
            scan = create_scan_msg(frame_id, moved, scan_time)
        else:
            scan = create_scan_msg(frame_id, obstacles, scan_time)

        pub.publish(scan)
        t += scan_time
        rate.sleep()


if __name__ == "__main__":
    main()
