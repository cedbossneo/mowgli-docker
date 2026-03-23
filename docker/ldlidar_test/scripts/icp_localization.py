#!/usr/bin/env python3
"""
ICP-based lidar localization for GPS FLOAT recovery.

Architecture:
- During GPS FIX: accumulates lidar scan points in map frame to build
  a reference point cloud of obstacle features (trees, posts, etc.)
- During GPS FLOAT: matches current scan against reference map using
  ICP (Iterative Closest Point) to compute absolute position correction
- Publishes corrected position on /icp/position so it can be fused
  or used as GPS substitute

This node is designed to work on both simulation and real hardware.
It only needs:
- /scan (LaserScan)
- map->base_link TF (from xbot_positioning)
- /ll/position/gps (to detect FIX/FLOAT state)

ICP algorithm (numpy-only, no scipy needed):
1. Convert current scan to 2D point cloud in map frame
2. For each point, find nearest neighbor in reference map (KD-tree-like)
3. Compute rigid transform (rotation + translation) minimizing distances
4. Iterate until convergence
"""

import math
import numpy as np
import rospy
import tf2_ros
import tf.transformations as tft
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Quaternion, Vector3
from xbot_msgs.msg import AbsolutePose


class ICPLocalizer:
    def __init__(self):
        rospy.init_node("icp_localizer", anonymous=False)

        # Reference map: accumulated point cloud from FIX scans in map frame
        self.ref_points = np.empty((0, 2))  # Nx2 array of (x, y) in map frame
        self.ref_grid = {}  # spatial hash for fast nearest neighbor
        self.grid_cell_size = 0.1  # 10cm grid cells for NN lookup

        # State
        self.gps_fix = False
        self.last_fix_time = 0.0
        self.icp_position = None  # (x, y, theta) from ICP
        self.last_icp_time = 0.0

        # Config
        self.ref_max_points = 5000  # max points in reference map
        self.ref_min_points = 50  # min points before ICP can work
        self.icp_max_iter = 20
        self.icp_tolerance = 0.001  # convergence threshold (meters)
        self.icp_max_dist = 0.5  # max correspondence distance
        self.scan_subsample = 3  # use every Nth scan point
        self.ref_accumulate_interval = 1.0  # seconds between ref additions

        self.last_ref_add_time = 0.0

        # TF
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)

        # Subscribe to GPS for FIX/FLOAT detection
        rospy.Subscriber("/ll/position/gps", AbsolutePose, self._gps_cb)

        # Subscribe to laser scan
        rospy.Subscriber("/scan", LaserScan, self._scan_cb)

        # Publish ICP-corrected position on /ll/position/gps
        # xbot_positioning subscribes to this and accepts FIX-flagged updates
        self.icp_pub = rospy.Publisher(
            "/ll/position/gps", AbsolutePose, queue_size=10
        )
        # Also publish on /icp/position for monitoring
        self.icp_debug_pub = rospy.Publisher(
            "/icp/position", AbsolutePose, queue_size=10
        )

        rospy.loginfo("[ICP] ICP Localizer started")
        rospy.loginfo("[ICP]   ref_max_points=%d, icp_max_iter=%d",
                      self.ref_max_points, self.icp_max_iter)

    def _gps_cb(self, msg):
        """Detect GPS FIX/FLOAT from flags.

        We track our own publishing to avoid reacting to ICP-generated
        messages (which always have FIX flag set).
        """
        # Skip messages we published ourselves (they always have accuracy < 0.1)
        # Real GPS FIX has accuracy 0.014, real FLOAT has accuracy 0.5
        # ICP messages have accuracy 0.03-0.1
        # Use FLOAT flag to detect real FLOAT vs ICP-corrected
        is_float = bool(msg.flags & AbsolutePose.FLAG_GPS_RTK_FLOAT)

        was_fix = self.gps_fix
        if is_float:
            self.gps_fix = False
        elif msg.position_accuracy < 0.02:
            # Real RTK FIX (accuracy ~0.014)
            self.gps_fix = True
            self.last_fix_time = rospy.get_time()
        # else: ICP message (FIX flag, accuracy 0.03-0.1) — don't change state

        if self.gps_fix and not was_fix:
            rospy.loginfo("[ICP] GPS FIX detected — accumulating reference map")
        elif not self.gps_fix and was_fix:
            rospy.loginfo("[ICP] GPS FLOAT — switching to ICP localization "
                          "(ref_points=%d)", len(self.ref_points))

    def _get_robot_pose(self):
        """Get current robot pose from TF (map->base_link)."""
        try:
            tf_stamped = self.tf_buffer.lookup_transform(
                "map", "base_link", rospy.Time(0), rospy.Duration(0.1)
            )
            x = tf_stamped.transform.translation.x
            y = tf_stamped.transform.translation.y
            q = tf_stamped.transform.rotation
            _, _, theta = tft.euler_from_quaternion([q.x, q.y, q.z, q.w])
            return x, y, theta
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException,
                tf2_ros.ExtrapolationException):
            return None

    def _scan_to_points(self, scan, robot_x, robot_y, robot_theta):
        """Convert LaserScan to 2D points in map frame."""
        points = []
        for i in range(0, len(scan.ranges), self.scan_subsample):
            r = scan.ranges[i]
            if r < scan.range_min or r > scan.range_max - 0.1:
                continue
            angle = scan.angle_min + i * scan.angle_increment
            # Point in robot frame
            lx = r * math.cos(angle)
            ly = r * math.sin(angle)
            # Transform to map frame
            cos_t = math.cos(robot_theta)
            sin_t = math.sin(robot_theta)
            mx = robot_x + lx * cos_t - ly * sin_t
            my = robot_y + lx * sin_t + ly * cos_t
            points.append((mx, my))
        return np.array(points) if points else np.empty((0, 2))

    def _add_to_grid(self, points):
        """Add points to spatial hash grid for fast NN lookup."""
        for p in points:
            cx = int(p[0] / self.grid_cell_size)
            cy = int(p[1] / self.grid_cell_size)
            key = (cx, cy)
            if key not in self.ref_grid:
                self.ref_grid[key] = []
            self.ref_grid[key].append(p)

    def _rebuild_grid(self):
        """Rebuild spatial hash from ref_points."""
        self.ref_grid = {}
        self._add_to_grid(self.ref_points)

    def _find_nearest(self, point):
        """Find nearest reference point using spatial hash."""
        cx = int(point[0] / self.grid_cell_size)
        cy = int(point[1] / self.grid_cell_size)
        best_dist = float('inf')
        best_point = None
        # Search 3x3 neighborhood
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                key = (cx + dx, cy + dy)
                if key in self.ref_grid:
                    for rp in self.ref_grid[key]:
                        d = (point[0] - rp[0]) ** 2 + (point[1] - rp[1]) ** 2
                        if d < best_dist:
                            best_dist = d
                            best_point = rp
        return best_point, math.sqrt(best_dist) if best_point is not None else float('inf')

    def _accumulate_reference(self, scan, robot_x, robot_y, robot_theta):
        """Add current scan points to reference map during GPS FIX."""
        now = rospy.get_time()
        if now - self.last_ref_add_time < self.ref_accumulate_interval:
            return
        self.last_ref_add_time = now

        new_points = self._scan_to_points(scan, robot_x, robot_y, robot_theta)
        if len(new_points) == 0:
            return

        # Filter: only add points that are >5cm from existing reference points
        # (avoids duplicating the same obstacle from multiple scans)
        filtered = []
        for p in new_points:
            _, dist = self._find_nearest(p)
            if dist > 0.05:
                filtered.append(p)

        if not filtered:
            return

        filtered = np.array(filtered)
        self.ref_points = np.vstack([self.ref_points, filtered])

        # If we exceed max points, downsample by keeping every other point
        if len(self.ref_points) > self.ref_max_points:
            indices = np.random.choice(
                len(self.ref_points), self.ref_max_points, replace=False
            )
            self.ref_points = self.ref_points[indices]
            self._rebuild_grid()
        else:
            self._add_to_grid(filtered)

    def _icp_match(self, scan_points, initial_x, initial_y, initial_theta):
        """Run ICP to align scan_points against reference map.

        Returns (x, y, theta, error) or None if failed.
        Uses point-to-point ICP with SVD for rigid transform computation.
        """
        if len(scan_points) < 10 or len(self.ref_points) < self.ref_min_points:
            return None

        # Work with scan points in robot-local frame (relative to initial pose)
        # We'll transform them to map frame using the current estimate
        cos_t = math.cos(initial_theta)
        sin_t = math.sin(initial_theta)

        # Convert scan points from map frame (computed with initial pose) to local
        local_points = np.copy(scan_points)
        local_points[:, 0] -= initial_x
        local_points[:, 1] -= initial_y
        rotated = np.empty_like(local_points)
        rotated[:, 0] = local_points[:, 0] * cos_t + local_points[:, 1] * sin_t
        rotated[:, 1] = -local_points[:, 0] * sin_t + local_points[:, 1] * cos_t
        local_scan = rotated  # points in robot-local frame

        # Current transform estimate
        tx, ty, ta = initial_x, initial_y, initial_theta

        for iteration in range(self.icp_max_iter):
            # Transform local scan to map frame with current estimate
            cos_a = math.cos(ta)
            sin_a = math.sin(ta)
            transformed = np.empty_like(local_scan)
            transformed[:, 0] = local_scan[:, 0] * cos_a - local_scan[:, 1] * sin_a + tx
            transformed[:, 1] = local_scan[:, 0] * sin_a + local_scan[:, 1] * cos_a + ty

            # Find correspondences
            src_pts = []
            dst_pts = []
            for i in range(len(transformed)):
                nearest, dist = self._find_nearest(transformed[i])
                if nearest is not None and dist < self.icp_max_dist:
                    src_pts.append(local_scan[i])
                    dst_pts.append(nearest)

            if len(src_pts) < 5:
                return None

            src = np.array(src_pts)
            dst = np.array(dst_pts)

            # Compute rigid transform using SVD
            src_mean = np.mean(src, axis=0)
            dst_mean = np.mean(dst, axis=0)
            src_centered = src - src_mean
            dst_centered = dst - dst_mean

            H = src_centered.T @ dst_centered
            U, _, Vt = np.linalg.svd(H)
            R = Vt.T @ U.T

            # Ensure proper rotation (det = 1)
            if np.linalg.det(R) < 0:
                Vt[-1, :] *= -1
                R = Vt.T @ U.T

            t = dst_mean - R @ src_mean

            # Extract angle from rotation matrix
            new_angle = math.atan2(R[1, 0], R[0, 0])

            # Update transform
            old_tx, old_ty, old_ta = tx, ty, ta
            tx = t[0]
            ty = t[1]
            ta = new_angle

            # Check convergence
            dt = math.sqrt((tx - old_tx) ** 2 + (ty - old_ty) ** 2)
            da = abs(ta - old_ta)
            if dt < self.icp_tolerance and da < 0.001:
                break

        # Compute final error
        cos_a = math.cos(ta)
        sin_a = math.sin(ta)
        final_transformed = np.empty_like(local_scan)
        final_transformed[:, 0] = local_scan[:, 0] * cos_a - local_scan[:, 1] * sin_a + tx
        final_transformed[:, 1] = local_scan[:, 0] * sin_a + local_scan[:, 1] * cos_a + ty

        total_error = 0.0
        n_matched = 0
        for i in range(len(final_transformed)):
            _, dist = self._find_nearest(final_transformed[i])
            if dist < self.icp_max_dist:
                total_error += dist
                n_matched += 1

        if n_matched < 5:
            return None

        mean_error = total_error / n_matched
        return tx, ty, ta, mean_error

    def _publish_icp_position(self, x, y, theta, accuracy):
        """Publish ICP-corrected position as AbsolutePose."""
        msg = AbsolutePose()
        msg.header.stamp = rospy.Time.now()
        msg.header.frame_id = "map"
        msg.source = AbsolutePose.SOURCE_GPS

        # Mark as FIX so xbot_positioning accepts it
        msg.flags = AbsolutePose.FLAG_GPS_RTK | AbsolutePose.FLAG_GPS_RTK_FIXED
        msg.position_accuracy = accuracy
        msg.orientation_valid = 1
        msg.motion_vector_valid = 1
        msg.orientation_accuracy = 0.1

        msg.pose.pose.position.x = x
        msg.pose.pose.position.y = y
        q = tft.quaternion_from_euler(0, 0, theta)
        msg.pose.pose.orientation = Quaternion(*q)

        cov = accuracy * accuracy
        msg.pose.covariance = [0.0] * 36
        msg.pose.covariance[0] = cov
        msg.pose.covariance[7] = cov
        msg.pose.covariance[14] = 0.1
        msg.pose.covariance[35] = 0.01

        msg.vehicle_heading = theta
        msg.motion_heading = theta
        msg.motion_vector = Vector3(x=0, y=0, z=0)

        self.icp_pub.publish(msg)
        self.icp_debug_pub.publish(msg)

    def _scan_cb(self, scan):
        """Process incoming laser scan."""
        pose = self._get_robot_pose()
        if pose is None:
            return
        robot_x, robot_y, robot_theta = pose

        if self.gps_fix:
            # During FIX: accumulate reference map
            self._accumulate_reference(scan, robot_x, robot_y, robot_theta)
        else:
            # During FLOAT: run ICP matching
            if len(self.ref_points) < self.ref_min_points:
                return

            scan_points = self._scan_to_points(
                scan, robot_x, robot_y, robot_theta
            )
            if len(scan_points) < 10:
                return

            result = self._icp_match(
                scan_points, robot_x, robot_y, robot_theta
            )
            if result is not None:
                icp_x, icp_y, icp_theta, error = result
                # Only use ICP result if error is reasonable
                if error < 0.2:
                    self.icp_position = (icp_x, icp_y, icp_theta)
                    self.last_icp_time = rospy.get_time()
                    # Accuracy based on ICP error (minimum 3cm)
                    accuracy = max(0.03, min(0.1, error * 2))
                    self._publish_icp_position(icp_x, icp_y, icp_theta, accuracy)

                    rospy.loginfo_throttle(
                        5.0,
                        f"[ICP] pos=({icp_x:.2f},{icp_y:.2f}) "
                        f"err={error:.3f}m ref={len(self.ref_points)} "
                        f"acc={accuracy:.3f}m"
                    )
                else:
                    rospy.logwarn_throttle(
                        5.0,
                        f"[ICP] High error: {error:.3f}m — skipping"
                    )


def main():
    node = ICPLocalizer()
    rospy.spin()


if __name__ == "__main__":
    main()
