from gym import utils
import copy
import rospy
from gym import spaces
from openai_ros.robot_envs import fetch_env
from gym.envs.registration import register
import numpy as np
from sensor_msgs.msg import JointState


register(
        id='FetchTest-v0',
        entry_point='openai_ros:task_envs.fetch.fetch_test_task.FetchTestEnv',
        timestep_limit=50,
    )
    

class FetchTestEnv(fetch_env.FetchEnv, utils.EzPickle):
    def __init__(self):
        
        #print("Entered FetchTestEnv Env")
        self.get_params()
        
        fetch_env.FetchEnv.__init__(self)

        
        self.action_space = spaces.Discrete(self.n_actions)
        
        observations_high_range = np.array([self.position_ee_max]*self.n_observations)
        observations_low_range = np.array([self.position_ee_min]*self.n_observations)
        
        observations_high_dist = np.array([self.max_distance])
        observations_low_dist = np.array([0.0])
        
        high = np.concatenate([observations_high_range, observations_high_dist])
        low = np.concatenate([observations_low_range, observations_low_dist])
        
        self.observation_space = spaces.Box(low, high)
        

        
    def get_params(self):
        #get configuration parameters
        
        self.n_actions = rospy.get_param('/fetch/n_actions')
        self.n_observations = rospy.get_param('/fetch/n_observations')
        self.position_ee_max = rospy.get_param('/fetch/position_ee_max')
        self.position_ee_min = rospy.get_param('/fetch/position_ee_min')
        
        self.init_pos = rospy.get_param('/fetch/init_pos')
        self.setup_ee_pos = rospy.get_param('/fetch/setup_ee_pos')
        self.goal_ee_pos = rospy.get_param('/fetch/goal_ee_pos')
        
        self.position_delta = rospy.get_param('/fetch/position_delta')
        self.step_punishment = rospy.get_param('/fetch/step_punishment')
        self.closer_reward = rospy.get_param('/fetch/closer_reward')
        self.impossible_movement_punishement = rospy.get_param('/fetch/impossible_movement_punishement')
        self.reached_goal_reward = rospy.get_param('/fetch/reached_goal_reward')
        
        self.max_distance = rospy.get_param('/fetch/max_distance')
        
        self.desired_position = [self.goal_ee_pos["x"],self.goal_ee_pos["y"],self.goal_ee_pos["z"]]
        self.gripper_rotation = [1., 0., 1., 0.]
    
    
    def _set_init_pose(self):
        """Sets the Robot in its init pose
        The Simulation will be unpaused for this purpose.
        """
        # Check because it seems its not being used
        #print("Init Pos:")
        #print(self.init_pos)

        """
        # Init Joint Pose
        #print("Moving To SETUP Joints ")
        self.movement_result = self.set_trajectory_joints(self.init_pos)
        """
        
        # We test the Desired Goal
        
        # INIT POSE
        #print("Moving To TEST DESIRED GOAL Position ")
        action = self.create_action(self.desired_position,self.gripper_rotation)
        self.movement_result = self.set_trajectory_ee(action)
            
        
        if self.movement_result:
            # INIT POSE
            #print("Moving To SETUP Position ")
            self.last_gripper_target = [self.setup_ee_pos["x"],self.setup_ee_pos["y"],self.setup_ee_pos["z"]]
            action = self.create_action(self.last_gripper_target,self.gripper_rotation)
            self.movement_result = self.set_trajectory_ee(action)
            
            self.current_dist_from_des_pos_ee = self.calculate_distance_between(self.desired_position,self.last_gripper_target)
            #print("INIT DISTANCE FROM GOAL==>"+str(self.current_dist_from_des_pos_ee))
        else:
            assert False, "Desired GOAL EE is not possible"
        
        self.last_action = "INIT"
        
        #print("Init Pose Results ==>"+str(self.movement_result))

        return self.movement_result


    def _init_env_variables(self):
        """
        Inits variables needed to be initialised each time we reset at the start
        of an episode.
        The simulation will be paused, therefore all the data retrieved has to be 
        from a system that doesnt need the simulation running, like variables where the 
        callbackas have stored last know sesnor data.
        :return:
        """
        #print("Init Env Variables...")
        #print("Init Env Variables...END")
    

    def _set_action(self, action):
        
        
        delta_gripper_target = [0.0]*len(self.last_gripper_target)
        
        
        # We convert action ints in increments/decrements of one of the axis XYZ
        if action == 0: # X+
            delta_gripper_target[0] += self.position_delta
            self.last_action = "X+"
        elif action == 1: # X-
            delta_gripper_target[0] -= self.position_delta
            self.last_action = "X-"
        elif action == 2: # Y+
            delta_gripper_target[1] += self.position_delta
            self.last_action = "Y+"
        elif action == 3: # Y-
            delta_gripper_target[1] -= self.position_delta
            self.last_action = "Y-"
        elif action == 4: #Z+
            delta_gripper_target[2] += self.position_delta
            self.last_action = "Z+"
        elif action == 5: #Z-
            delta_gripper_target[2] -= self.position_delta
            self.last_action = "Z-"
        
        
        gripper_target = copy.deepcopy(self.last_gripper_target)
        gripper_target[0] += delta_gripper_target[0]
        gripper_target[1] += delta_gripper_target[1]
        gripper_target[2] += delta_gripper_target[2]
        
        # Apply action to simulation.
        action_end_effector = self.create_action(gripper_target,self.gripper_rotation)
        self.movement_result = self.set_trajectory_ee(action_end_effector)
        if self.movement_result:
            # If the End Effector Positioning was succesfull, we replace the last one with the new one.
            self.last_gripper_target = copy.deepcopy(gripper_target)
        else:
            rospy.logerr("Impossible End Effector Position...."+str(gripper_target))
        
        #print("END Set Action ==>"+str(action)+", NAME="+str(self.last_action))

    def _get_obs(self):
        """
        It returns the Position of the TCP/EndEffector as observation.
        And the distance from the desired point
        Orientation for the moment is not considered
        """
        
        grip_pos = self.get_ee_pose()
        grip_pos_array = [grip_pos.pose.position.x, grip_pos.pose.position.y, grip_pos.pose.position.z]
        obs = grip_pos_array
        
        new_dist_from_des_pos_ee = self.calculate_distance_between(self.desired_position,grip_pos_array)
        
        obs.append(new_dist_from_des_pos_ee)

        #print("OBSERVATIONS====>>>>>>>"+str(obs))

        return obs
        
    def _is_done(self, observations):
        
        """
        If the latest Action didnt succeed, it means that tha position asked was imposible therefore the episode must end.
        It will also end if it reaches its goal.
        """
        
        current_pos = observations[:3]
        
        done = self.calculate_if_done(self.movement_result,self.desired_position,current_pos)
        
        return done
        
    def _compute_reward(self, observations, done):

        """
        We punish each step that it passes without achieveing the goal.
        Punishes differently if it reached a position that is imposible to move to.
        Rewards getting to a position close to the goal.
        """
        current_pos = observations[:3]
        new_dist_from_des_pos_ee = observations[-1]
        
        reward = self.calculate_reward(self.movement_result, self.desired_position, current_pos, new_dist_from_des_pos_ee)
        #print(">>>REWARD>>>"+str(reward))
        
        return reward
        

    def calculate_if_done(self, movement_result,desired_position,current_pos):
        """
        It calculated whather it has finished or not
        """
        done = False
        
        if movement_result:
            
            position_similar = np.all(np.isclose(desired_position, current_pos, atol=1e-02))

            if position_similar:
                done = True
                #print("Reached a Desired Position!")
        else:
            done = True
            #print("Reached a TCP position not reachable")
            
        return done
        
    
    def calculate_reward(self, movement_result, desired_position, current_pos, new_dist_from_des_pos_ee):
        """
        It calculated whather it has finished or nota and how much reward to give
        """

        if movement_result:
            position_similar = np.all(np.isclose(desired_position, current_pos, atol=1e-02))
            
            # Calculating Distance
            #print("desired_position="+str(desired_position))
            #print("current_pos="+str(current_pos))
            #print("self.current_dist_from_des_pos_ee="+str(self.current_dist_from_des_pos_ee))
            #print("new_dist_from_des_pos_ee="+str(new_dist_from_des_pos_ee))
            
            delta_dist = new_dist_from_des_pos_ee - self.current_dist_from_des_pos_ee
            if position_similar:
                reward = self.reached_goal_reward
                #print("Reached a Desired Position!")
            else:
                if delta_dist < 0:
                    reward = self.closer_reward
                    #print("CLOSER To Desired Position!="+str(delta_dist))
                else:
                    reward = self.step_punishment
                    #print("FURTHER FROM Desired Position!"+str(delta_dist))
            
        else:
            reward = self.impossible_movement_punishement
            #print("Reached a TCP position not reachable")
            
        # We update the distance
        self.current_dist_from_des_pos_ee = new_dist_from_des_pos_ee
        #print("Updated Distance from GOAL=="+str(self.current_dist_from_des_pos_ee))
            
        return reward
        
    def calculate_distance_between(self,v1,v2):
        """
        Calculated the Euclidian distance between two vectors given as python lists.
        """
        dist = np.linalg.norm(np.array(v1)-np.array(v2))
        return dist