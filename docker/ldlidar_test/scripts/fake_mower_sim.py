#!/usr/bin/env python3
"""
Full mower simulation for offline testing with OpenMower + Mowgli stack.

Publishes all topics that the Mowgli firmware normally sends via rosserial:
- /ll/mower_status       (mower_msgs/Status)
- /ll/power              (mower_msgs/Power)
- /ll/emergency          (mower_msgs/Emergency)
- /ll/diff_drive/left_esc_status  (mower_msgs/ESCStatus)
- /ll/diff_drive/right_esc_status (mower_msgs/ESCStatus)
- /ll/imu/data_raw       (sensor_msgs/Imu)
- /ll/diff_drive/measured_twist   (geometry_msgs/TwistStamped)
- /ll/position/gps       (xbot_msgs/AbsolutePose)
- /scan                  (sensor_msgs/LaserScan)

Provides services (stubs for mower_comms):
- ll/_service/mow_enabled   (mower_msgs/MowerControlSrv)
- ll/_service/emergency      (mower_msgs/EmergencyStopSrv)

Subscribes to:
- /ll/cmd_vel            (geometry_msgs/Twist) from OpenMower navigation

Position model:
- Ground truth: integrated from cmd_vel (like real wheel encoders)
- GPS: reports ground truth + noise/drift (like real GPS)
- Lidar: computed from EKF position (via TF lookup) so obstacles stay fixed
  on the costmap. Falls back to ground truth before EKF is ready.

GPS cycles between RTK FIX and FLOAT.
"""

import os
import math
import time
import random
import rospy
import tf2_ros
import tf.transformations as tft
from sensor_msgs.msg import LaserScan, Imu
from nav_msgs.msg import Odometry
from geometry_msgs.msg import (
    TransformStamped, Quaternion, Twist,
    TwistStamped, PoseWithCovariance, Pose, Point, Vector3
)
from std_msgs.msg import Bool, Float32

# These are available via multi-stage Docker build from OpenMower image
from xbot_msgs.msg import AbsolutePose
from mower_msgs.msg import Status, Power, Emergency, ESCStatus
from mower_msgs.srv import (
    MowerControlSrv, MowerControlSrvResponse,
    EmergencyStopSrv, EmergencyStopSrvResponse,
)


class MowerSimulator:
    def __init__(self):
        rospy.init_node("mower_simulator", anonymous=False)

        # Config
        self.speed = float(os.environ.get("SIM_SPEED", "0.3"))
        self.area_w = float(os.environ.get("SIM_AREA_WIDTH", "10"))
        self.area_h = float(os.environ.get("SIM_AREA_HEIGHT", "8"))
        self.gps_fix_ratio = float(os.environ.get("SIM_GPS_FIX_RATIO", "0.7"))
        self.gps_float_drift = float(os.environ.get("SIM_GPS_FLOAT_DRIFT", "0.5"))
        self.lidar_topic = os.environ.get("LIDAR_TOPIC", "/scan")
        self.lidar_frame = os.environ.get("LIDAR_FRAME_ID", "base_laser")

        obs_str = os.environ.get("SIM_OBSTACLES", "3:4:0.3,7:2:0.5,5:6:0.4")
        self.obstacles = self._parse_obstacles(obs_str)

        # Ground truth position — integrated from cmd_vel (like real encoders)
        self.x = float(os.environ.get("SIM_START_X", "1.0"))
        self.y = float(os.environ.get("SIM_START_Y", "1.0"))
        self.theta = 0.0
        self.vx = 0.0
        self.vtheta = 0.0

        # EKF-estimated position (for lidar computation only)
        self.ekf_x = self.x
        self.ekf_y = self.y
        self.ekf_theta = self.theta
        self.ekf_available = False

        # GPS state
        self.gps_fix = True
        self.gps_drift_x = 0.0
        self.gps_drift_y = 0.0

        # Wheel tick simulation
        self.left_ticks = 0
        self.right_ticks = 0
        self.wheel_ticks_per_m = 300.0
        self.wheel_distance = 0.325

        # Subscribe to velocity commands from OpenMower
        self.cmd_vel_received = False
        self.cmd_vx = 0.0
        self.cmd_vtheta = 0.0
        self.last_cmd_time = 0.0
        rospy.Subscriber("/ll/cmd_vel", Twist, self._cmd_vel_cb)

        # --- Publishers matching Mowgli firmware ---

        # Sensor data
        self.imu_pub = rospy.Publisher("/ll/imu/data_raw", Imu, queue_size=10)
        self.twist_pub = rospy.Publisher(
            "/ll/diff_drive/measured_twist", TwistStamped, queue_size=10
        )
        self.gps_pub = rospy.Publisher(
            "/ll/position/gps", AbsolutePose, queue_size=10
        )
        self.scan_pub = rospy.Publisher(self.lidar_topic, LaserScan, queue_size=10)

        # Mowgli firmware status topics
        self.status_pub = rospy.Publisher("/ll/mower_status", Status, queue_size=10)
        self.power_pub = rospy.Publisher("/ll/power", Power, queue_size=10)
        self.emergency_pub = rospy.Publisher(
            "/ll/emergency", Emergency, queue_size=10, latch=True
        )
        self.left_esc_pub = rospy.Publisher(
            "/ll/diff_drive/left_esc_status", ESCStatus, queue_size=10
        )
        self.right_esc_pub = rospy.Publisher(
            "/ll/diff_drive/right_esc_status", ESCStatus, queue_size=10
        )

        # Service stubs (normally provided by mower_comms via rosserial)
        self.mow_enabled = False
        rospy.Service(
            "ll/_service/mow_enabled", MowerControlSrv, self._handle_mow_enabled
        )
        rospy.Service(
            "ll/_service/emergency", EmergencyStopSrv, self._handle_emergency
        )

        # TF listener — read EKF's map->base_link for lidar computation
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)

        # TF — only publish static transforms (lidar, gps frames on base_link)
        # DO NOT publish map->base_link: xbot_positioning + EKF own that transform.
        self.static_tf_broadcaster = tf2_ros.StaticTransformBroadcaster()
        self._publish_static_tfs()

        rospy.loginfo("=== Mowgli Mower Simulator ===")
        rospy.loginfo(f"  Area: {self.area_w}x{self.area_h}m, Speed: {self.speed} m/s")
        rospy.loginfo(f"  GPS fix ratio: {self.gps_fix_ratio}, Obstacles: {len(self.obstacles)}")
        rospy.loginfo("  GPS: ground truth + noise | Lidar: EKF position (TF)")
        rospy.loginfo("  Subscribing: /ll/cmd_vel")

    def _cmd_vel_cb(self, msg):
        self.cmd_vel_received = True
        self.cmd_vx = msg.linear.x
        self.cmd_vtheta = msg.angular.z
        self.last_cmd_time = time.time()

    def _handle_mow_enabled(self, req):
        self.mow_enabled = bool(req.mow_enabled)
        rospy.loginfo(f"[SIM] Mow enabled: {self.mow_enabled}")
        return MowerControlSrvResponse()

    def _handle_emergency(self, req):
        rospy.loginfo(f"[SIM] Emergency stop: {req.emergency}")
        return EmergencyStopSrvResponse()

    def _parse_obstacles(self, s):
        obstacles = []
        if not s:
            return obstacles
        for part in s.split(","):
            vals = part.strip().split(":")
            if len(vals) == 3:
                obstacles.append((float(vals[0]), float(vals[1]), float(vals[2])))
        return obstacles

    def _publish_static_tfs(self):
        transforms = []
        t = TransformStamped()
        t.header.stamp = rospy.Time.now()
        t.header.frame_id = "base_link"
        t.child_frame_id = self.lidar_frame
        t.transform.translation.z = 0.18
        t.transform.rotation.w = 1.0
        transforms.append(t)

        t2 = TransformStamped()
        t2.header.stamp = rospy.Time.now()
        t2.header.frame_id = "base_link"
        t2.child_frame_id = "gps"
        t2.transform.translation.x = 0.3
        t2.transform.rotation.w = 1.0
        transforms.append(t2)

        self.static_tf_broadcaster.sendTransform(transforms)

    def _update_ekf_position(self):
        """Read the EKF's map->base_link for lidar scan computation."""
        try:
            tf_stamped = self.tf_buffer.lookup_transform(
                "map", "base_link", rospy.Time(0), rospy.Duration(0.05)
            )
            self.ekf_x = tf_stamped.transform.translation.x
            self.ekf_y = tf_stamped.transform.translation.y
            q = tf_stamped.transform.rotation
            _, _, yaw = tft.euler_from_quaternion([q.x, q.y, q.z, q.w])
            self.ekf_theta = yaw
            if not self.ekf_available:
                rospy.loginfo("[SIM] EKF position available — lidar using EKF pose")
                self.ekf_available = True
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException,
                tf2_ros.ExtrapolationException):
            # EKF not ready yet, fall back to ground truth
            self.ekf_x = self.x
            self.ekf_y = self.y
            self.ekf_theta = self.theta

    def _update_position(self, dt):
        """Integrate ground truth position from cmd_vel (like real encoders)."""
        # Follow cmd_vel from OpenMower; stop if nothing received
        if self.cmd_vel_received and (time.time() - self.last_cmd_time) < 1.0:
            self.vx = self.cmd_vx
            self.vtheta = self.cmd_vtheta
        else:
            if self.cmd_vel_received:
                self.cmd_vel_received = False
                rospy.loginfo("[SIM] Lost cmd_vel, stopping")
            self.vx = 0.0
            self.vtheta = 0.0

        # Obstacle collision: stop forward motion if inside obstacle
        # but always allow rotation so the robot can turn away
        for ox, oy, orad in self.obstacles:
            odist = math.sqrt((ox - self.x) ** 2 + (oy - self.y) ** 2)
            if odist < orad:
                self.vx = 0.0
                # Allow vtheta so robot can rotate away from obstacle
                break

        # Integrate
        self.theta += self.vtheta * dt
        self.theta = math.atan2(math.sin(self.theta), math.cos(self.theta))
        self.x += self.vx * math.cos(self.theta) * dt
        self.y += self.vx * math.sin(self.theta) * dt
        self.x = max(-0.5, min(self.area_w + 0.5, self.x))
        self.y = max(-1.0, min(self.area_h + 0.5, self.y))

        # Update wheel ticks
        v_left = self.vx - self.vtheta * self.wheel_distance / 2.0
        v_right = self.vx + self.vtheta * self.wheel_distance / 2.0
        self.left_ticks += int(v_left * dt * self.wheel_ticks_per_m)
        self.right_ticks += int(v_right * dt * self.wheel_ticks_per_m)

    def _update_gps_state(self, t):
        # Grace period: always FIX for the first 60s so OpenMower can initialize
        startup_grace = 60.0
        if t < startup_grace:
            if not self.gps_fix:
                self.gps_fix = True
                self.gps_drift_x = 0.0
                self.gps_drift_y = 0.0
            return

        cycle = 30.0
        phase = ((t - startup_grace) % cycle) / cycle
        was_fix = self.gps_fix
        self.gps_fix = phase < self.gps_fix_ratio

        if self.gps_fix and not was_fix:
            rospy.loginfo("[GPS] Regained RTK FIX")
            self.gps_drift_x = 0.0
            self.gps_drift_y = 0.0
        elif not self.gps_fix and was_fix:
            rospy.loginfo("[GPS] Degraded to FLOAT")

        if not self.gps_fix:
            # Realistic FLOAT drift — GPS wanders without RTK correction
            drift_rate = self.gps_float_drift * 0.1
            self.gps_drift_x += random.gauss(0, drift_rate * 0.1)
            self.gps_drift_y += random.gauss(0, drift_rate * 0.1)
            self.gps_drift_x = max(-self.gps_float_drift,
                                   min(self.gps_float_drift, self.gps_drift_x))
            self.gps_drift_y = max(-self.gps_float_drift,
                                   min(self.gps_float_drift, self.gps_drift_y))

    def _publish_twist(self):
        msg = TwistStamped()
        msg.header.stamp = rospy.Time.now()
        msg.header.frame_id = "base_link"
        msg.twist.linear.x = self.vx + random.gauss(0, 0.01)
        msg.twist.angular.z = self.vtheta + random.gauss(0, 0.005)
        self.twist_pub.publish(msg)

    def _publish_gps_pose(self):
        """Publish GPS from ground truth position + noise (like real GPS).

        During FIX: high-accuracy RTK GPS (1.4cm)
        During FLOAT: degraded GPS with drift (xbot_positioning will drop it)
        The ICP node provides position correction during FLOAT separately.
        """
        msg = AbsolutePose()
        msg.header.stamp = rospy.Time.now()
        msg.header.frame_id = "map"
        msg.source = AbsolutePose.SOURCE_GPS

        if self.gps_fix:
            msg.flags = AbsolutePose.FLAG_GPS_RTK | AbsolutePose.FLAG_GPS_RTK_FIXED
            msg.position_accuracy = 0.014
            gps_noise = 0.014
            cov = 0.014 * 0.014
        else:
            # Real FLOAT: high drift, xbot_positioning will drop this
            # ICP node provides corrected position on /ll/position/gps
            msg.flags = AbsolutePose.FLAG_GPS_RTK | AbsolutePose.FLAG_GPS_RTK_FLOAT
            msg.position_accuracy = 0.5
            gps_noise = 0.15
            cov = 1.0

        msg.orientation_valid = 1
        msg.motion_vector_valid = 1
        msg.orientation_accuracy = 0.1

        # GPS reports ground truth + noise + drift (during FLOAT)
        msg.pose.pose.position.x = self.x + self.gps_drift_x + random.gauss(0, gps_noise)
        msg.pose.pose.position.y = self.y + self.gps_drift_y + random.gauss(0, gps_noise)
        q = tft.quaternion_from_euler(0, 0, self.theta)
        msg.pose.pose.orientation = Quaternion(*q)

        msg.pose.covariance = [0.0] * 36
        msg.pose.covariance[0] = cov
        msg.pose.covariance[7] = cov
        msg.pose.covariance[14] = 0.1
        msg.pose.covariance[35] = 0.01

        msg.vehicle_heading = self.theta
        msg.motion_heading = self.theta
        msg.motion_vector = Vector3(
            x=self.vx * math.cos(self.theta),
            y=self.vx * math.sin(self.theta),
            z=0.0
        )
        self.gps_pub.publish(msg)

    def _publish_imu(self):
        msg = Imu()
        msg.header.stamp = rospy.Time.now()
        msg.header.frame_id = "imu"
        q = tft.quaternion_from_euler(0, 0, self.theta)
        msg.orientation = Quaternion(*q)
        msg.orientation_covariance = [0.01, 0, 0, 0, 0.01, 0, 0, 0, 0.01]
        msg.angular_velocity.z = self.vtheta + random.gauss(0, 0.01)
        msg.angular_velocity_covariance = [0.001, 0, 0, 0, 0.001, 0, 0, 0, 0.001]
        msg.linear_acceleration.x = random.gauss(0, 0.05)
        msg.linear_acceleration.y = random.gauss(0, 0.05)
        msg.linear_acceleration.z = 9.81 + random.gauss(0, 0.05)
        msg.linear_acceleration_covariance = [0.01, 0, 0, 0, 0.01, 0, 0, 0, 0.01]
        self.imu_pub.publish(msg)

    def _publish_status(self):
        """Publish Mowgli-compatible status topics."""
        now = rospy.Time.now()

        status = Status()
        status.stamp = now
        status.mow_enabled = False
        status.rain_detected = False
        status.is_charging = False
        status.mower_status = Status.MOWER_STATUS_OK
        status.raspberry_pi_power = True
        status.esc_power = True
        status.mower_esc_temperature = 25.0
        status.mower_esc_current = 0.0
        status.mower_motor_temperature = 25.0
        status.mower_motor_rpm = 0.0
        self.status_pub.publish(status)

        power = Power()
        power.stamp = now
        power.v_battery = 25.5
        power.v_charge = 0.0
        power.charge_current = 0.0
        self.power_pub.publish(power)

        emergency = Emergency()
        emergency.stamp = now
        emergency.active_emergency = False
        emergency.latched_emergency = False
        emergency.reason = ""
        self.emergency_pub.publish(emergency)

        for pub in [self.left_esc_pub, self.right_esc_pub]:
            esc = ESCStatus()
            esc.status = ESCStatus.ESC_STATUS_OK
            esc.current = abs(self.vx) * 2.0 + random.gauss(0, 0.1)
            esc.temperature_motor = 30.0 + random.gauss(0, 1)
            esc.temperature_pcb = 28.0 + random.gauss(0, 0.5)
            pub.publish(esc)

    def _publish_scan(self):
        """Compute lidar scan from EKF position.

        The costmap transforms scan hits from base_laser->map using the
        EKF's map->base_link TF. By computing ranges from the same EKF
        position, obstacles stay perfectly fixed on the costmap.
        Ground truth is only used for GPS (like on a real robot).
        """
        # Use EKF position for scan (consistent with costmap TF)
        scan_x = self.ekf_x
        scan_y = self.ekf_y
        scan_theta = self.ekf_theta

        scan = LaserScan()
        scan.header.stamp = rospy.Time.now()
        scan.header.frame_id = self.lidar_frame
        num_readings = 360
        scan.angle_min = 0.0
        scan.angle_max = 2.0 * math.pi
        scan.angle_increment = 2.0 * math.pi / num_readings
        scan.time_increment = 0.1 / num_readings
        scan.scan_time = 0.1
        scan.range_min = 0.05
        scan.range_max = 12.0

        ranges = [scan.range_max] * num_readings
        intensities = [0.0] * num_readings

        for i in range(num_readings):
            angle = scan.angle_min + i * scan.angle_increment
            ray_angle = scan_theta + angle

            for ox, oy, orad in self.obstacles:
                dx = ox - scan_x
                dy = oy - scan_y
                d2c = math.sqrt(dx * dx + dy * dy)
                if d2c > scan.range_max + orad:
                    continue
                a2o = math.atan2(dy, dx)
                adiff = math.atan2(math.sin(a2o - ray_angle), math.cos(a2o - ray_angle))
                ang_size = math.asin(min(1.0, orad / max(orad, d2c))) if d2c > orad else math.pi
                if abs(adiff) < ang_size:
                    hit = d2c * math.cos(adiff) - math.sqrt(
                        max(0, orad ** 2 - (d2c * math.sin(adiff)) ** 2))
                    if scan.range_min < hit < ranges[i]:
                        ranges[i] = hit
                        intensities[i] = 200.0

            # No boundary raycasting — sim area limits are not physical walls.
            # Only real obstacles produce lidar hits.

        scan.ranges = ranges
        scan.intensities = intensities
        self.scan_pub.publish(scan)

    def _ray_boundary_distances(self, rx, ry, cos_a, sin_a):
        """Compute distances to sim area boundaries from position (rx, ry)."""
        dists = []
        eps = 1e-9
        if cos_a > eps:
            d = (self.area_w - rx) / cos_a
            if 0 <= ry + d * sin_a <= self.area_h:
                dists.append(d)
        if cos_a < -eps:
            d = -rx / cos_a
            if 0 <= ry + d * sin_a <= self.area_h:
                dists.append(d)
        if sin_a > eps:
            d = (self.area_h - ry) / sin_a
            if 0 <= rx + d * cos_a <= self.area_w:
                dists.append(d)
        if sin_a < -eps:
            d = -ry / sin_a
            if 0 <= rx + d * cos_a <= self.area_w:
                dists.append(d)
        return dists

    def run(self):
        rate = rospy.Rate(50)  # 50 Hz like real firmware
        t_start = time.time()
        imu_counter = 0
        status_counter = 0

        while not rospy.is_shutdown():
            dt = 0.02  # 50Hz
            t = time.time() - t_start

            self._update_gps_state(t)
            self._update_position(dt)

            # IMU at 50Hz (every tick)
            self._publish_imu()

            # Wheel twist + GPS + lidar at 10Hz
            imu_counter += 1
            if imu_counter >= 5:
                imu_counter = 0
                self._publish_twist()
                self._publish_gps_pose()
                self._update_ekf_position()
                self._publish_scan()

            # Status at 4Hz
            status_counter += 1
            if status_counter >= 12:
                status_counter = 0
                self._publish_status()

            # Log every 5 seconds
            if int(t * 50) % 250 == 0:
                fix_str = "FIX" if self.gps_fix else "FLOAT"
                nav = "OM" if self.cmd_vel_received else "idle"
                drift = math.sqrt(
                    (self.x - self.ekf_x) ** 2 + (self.y - self.ekf_y) ** 2
                )
                rospy.loginfo(
                    f"[SIM] gt=({self.x:.1f},{self.y:.1f}) "
                    f"ekf=({self.ekf_x:.1f},{self.ekf_y:.1f}) "
                    f"d={drift:.2f}m "
                    f"h={math.degrees(self.theta):.0f}° "
                    f"GPS={fix_str} nav={nav}"
                )

            rate.sleep()


if __name__ == "__main__":
    sim = MowerSimulator()
    sim.run()
