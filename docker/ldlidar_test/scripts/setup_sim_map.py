#!/usr/bin/env python3
"""
Set up a fake mowing map and start mowing for simulation.
Waits for map_service to be ready, then:
1. Sets docking point
2. Adds mowing area with obstacle
3. Sends HOME (to exit area recording if active)
4. Sends START to begin mowing
"""
import math
import os
import rospy
from geometry_msgs.msg import Pose, Point, Quaternion, Point32, Polygon
from mower_map.srv import SetDockingPointSrv, AddMowingAreaSrv
from mower_map.msg import MapArea
from mower_msgs.srv import HighLevelControlSrv
import tf.transformations as tft


def main():
    rospy.init_node("sim_map_setup", anonymous=True)

    dock_x = float(os.environ.get("SIM_DOCK_X", "1.0"))
    dock_y = float(os.environ.get("SIM_DOCK_Y", "1.0"))

    # Mowing area: configurable rectangle inside the sim area
    area_x1 = float(os.environ.get("SIM_MOW_X1", "2.0"))
    area_y1 = float(os.environ.get("SIM_MOW_Y1", "2.0"))
    area_x2 = float(os.environ.get("SIM_MOW_X2", "8.0"))
    area_y2 = float(os.environ.get("SIM_MOW_Y2", "6.0"))

    rospy.loginfo("Waiting for mower_map_service...")
    rospy.wait_for_service("mower_map_service/set_docking_point", timeout=120)
    rospy.wait_for_service("mower_map_service/add_mowing_area", timeout=10)
    rospy.wait_for_service("mower_service/high_level_control", timeout=120)

    # 1. Docking point
    rospy.loginfo(f"Setting docking point at ({dock_x}, {dock_y})")
    dock_srv = rospy.ServiceProxy(
        "mower_map_service/set_docking_point", SetDockingPointSrv
    )
    q = tft.quaternion_from_euler(0, 0, 0)
    dock_srv(Pose(position=Point(dock_x, dock_y, 0), orientation=Quaternion(*q)))

    # 2. Mowing area
    rospy.loginfo(
        f"Adding mowing area ({area_x1},{area_y1})-({area_x2},{area_y2})"
    )
    add_area = rospy.ServiceProxy(
        "mower_map_service/add_mowing_area", AddMowingAreaSrv
    )
    area = MapArea()
    area.name = "sim_area"
    area.area = Polygon(
        points=[
            Point32(area_x1, area_y1, 0),
            Point32(area_x2, area_y1, 0),
            Point32(area_x2, area_y2, 0),
            Point32(area_x1, area_y2, 0),
        ]
    )

    # Add obstacle in the center of the mowing area
    obs_x = (area_x1 + area_x2) / 2.0
    obs_y = (area_y1 + area_y2) / 2.0
    obs_r = 0.4
    obs_points = []
    for i in range(8):
        angle = 2 * math.pi * i / 8
        obs_points.append(
            Point32(obs_x + obs_r * math.cos(angle), obs_y + obs_r * math.sin(angle), 0)
        )
    area.obstacles = [Polygon(points=obs_points)]
    add_area(area=area, isNavigationArea=False)

    # 2b. Add navigation area connecting dock to entire mowing area
    # Must cover: docking approach (dock_x - docking_dist), undock exit,
    # and the full Y range of the mowing area so the robot can return
    # from any mowing position back to the dock.
    docking_dist = 1.0  # matches OM_DOCKING_DISTANCE in mower_config_sim.sh
    rospy.loginfo("Adding navigation area (dock to mowing area)")
    nav_area = MapArea()
    nav_area.name = "nav_to_mow"
    nav_area.area = Polygon(
        points=[
            Point32(dock_x - docking_dist - 0.3, dock_y - 1.0, 0),
            Point32(area_x1 + 0.3, dock_y - 1.0, 0),
            Point32(area_x1 + 0.3, area_y2 + 0.3, 0),
            Point32(dock_x - docking_dist - 0.3, area_y2 + 0.3, 0),
        ]
    )
    nav_area.obstacles = []
    add_area(area=nav_area, isNavigationArea=True)

    # 3. HOME first (in case we're stuck in area recording)
    control = rospy.ServiceProxy(
        "mower_service/high_level_control", HighLevelControlSrv
    )
    rospy.loginfo("Sending HOME to ensure IDLE state...")
    control(command=2)  # COMMAND_HOME

    # Wait for state machine to enter IDLE
    rospy.loginfo("Waiting for IDLE state...")
    rospy.sleep(5.0)

    # 4. START mowing (retry to handle state machine timing)
    from mower_msgs.msg import HighLevelStatus
    for attempt in range(5):
        rospy.loginfo(f"Sending START command (attempt {attempt + 1}/5)...")
        control(command=1)  # COMMAND_START
        rospy.sleep(3.0)

        try:
            state_msg = rospy.wait_for_message(
                "/mower_logic/current_state", HighLevelStatus, timeout=2.0
            )
            if state_msg.state == 2:  # MOWING
                rospy.loginfo("Mower is now MOWING!")
                break
            rospy.loginfo(f"State is {state_msg.state_name}, retrying...")
        except Exception as e:
            rospy.logwarn(f"Could not read state: {e}")

    rospy.loginfo("Simulation map setup complete.")


if __name__ == "__main__":
    main()
