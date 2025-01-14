import rospy
import numpy
from gym import spaces
from openai_ros.robot_envs import shadow_tc_env
from gym.envs.registration import register
from geometry_msgs.msg import Point
from geometry_msgs.msg import Vector3
from tf.transformations import euler_from_quaternion

timestep_limit_per_episode = 10000 # Can be any Value

register(
        id='ShadowTcGetBall-v0',
        entry_point='openai_ros:task_envs.shadow_tc.learn_to_pick_ball.ShadowTcGetBallEnv',
        timestep_limit=timestep_limit_per_episode,
    )

class ShadowTcGetBallEnv(shadow_tc_env.ShadowTcEnv):
    def __init__(self):
        """
        Make ShadowTc learn how pick up a ball
        """
        
        # We execute this one before because there are some functions that this
        # TaskEnv uses that use variables from the parent class, like the effort limit fetch.
        super(ShadowTcGetBallEnv, self).__init__()
        
        # Here we will add any init functions prior to starting the MyRobotEnv
        
        
        # Only variable needed to be set here

        #print("Start ShadowTcGetBallEnv INIT...")
        number_actions = rospy.get_param('/shadow_tc/n_actions')
        self.action_space = spaces.Discrete(number_actions)
        
        # We set the reward range, which is not compulsory but here we do it.
        self.reward_range = (-numpy.inf, numpy.inf)
        
        
        self.movement_delta =rospy.get_param("/shadow_tc/movement_delta")
        
        self.work_space_x_max = rospy.get_param("/shadow_tc/work_space/x_max")
        self.work_space_x_min = rospy.get_param("/shadow_tc/work_space/x_min")
        self.work_space_y_max = rospy.get_param("/shadow_tc/work_space/y_max")
        self.work_space_y_min = rospy.get_param("/shadow_tc/work_space/y_min")
        self.work_space_z_max = rospy.get_param("/shadow_tc/work_space/z_max")
        self.work_space_z_min = rospy.get_param("/shadow_tc/work_space/z_min")
        
        
        self.dec_obs = rospy.get_param("/shadow_tc/number_decimals_precision_obs")
        
        self.acceptable_distance_to_ball = rospy.get_param("/shadow_tc/acceptable_distance_to_ball")
        
        
        # We place the Maximum and minimum values of observations
        # TODO: Fill when get_observations is done.
        
        
        high = numpy.array([self.work_space_x_max,
                            self.work_space_y_max,
                            self.work_space_z_max,
                            1,1,1])
                                        
        low = numpy.array([ self.work_space_x_min,
                            self.work_space_y_min,
                            self.work_space_z_min,
                            0,0,0])

        
        self.observation_space = spaces.Box(low, high)
        
        #print("ACTION SPACES TYPE===>"+str(self.action_space))
        #print("OBSERVATION SPACES TYPE===>"+str(self.observation_space))
        
        # Rewards
        
        self.done_reward =rospy.get_param("/shadow_tc/done_reward")
        self.closer_to_block_reward = rospy.get_param("/shadow_tc/closer_to_block_reward")

        self.cumulated_steps = 0.0

        #print("END shadow_tcGetBallEnv INIT...")

    def _set_init_pose(self):
        """
        Sets the UR5 arm to the initial position and the objects to the original position.
        """
        #print("START _set_init_pose...")
        # We set the angles to zero of the limb
        self.reset_scene()
        
        #print("END _set_init_pose...")
        return True


    def _init_env_variables(self):
        """
        Inits variables needed to be initialised each time we reset at the start
        of an episode.
        :return:
        """
        #print("START TaskEnv _init_env_variables")
        # For Info Purposes
        self.cumulated_reward = 0.0
        
        self.ball_pose = self.get_ball_pose()
        tcp_pose = self.get_tip_pose()
        #print("TCP POSE ===>"+str(tcp_pose))
        self.previous_distance_from_ball = self.get_distance_from_point(self.ball_pose.position, tcp_pose.position)

        #print("END TaskEnv _init_env_variables")
        
        

    def _set_action(self, action):
        """
        It sets the joints of shadow_tc based on the action integer given
        based on the action number given.
        :param action: The action integer that sets what movement to do next.
        """
        
        #print("Start Set Action ==>"+str(action))
       
        
        increment_vector = Vector3() 
        action_id="move"
        
        if action == 0: # Increase X
            increment_vector.x = self.movement_delta
        elif action == 1: # Decrease X
            increment_vector.x = -1*self.movement_delta
        elif action == 2: # Increase Y
            increment_vector.y = self.movement_delta
        elif action == 3: # Decrease Y
            increment_vector.y = -1*self.movement_delta
        elif action == 4: # Increase Z
            increment_vector.z = self.movement_delta
        elif action == 5: # Decrease Z
            increment_vector.z = -1*self.movement_delta
        elif action == 6: # Open Claw
            action_id = "open"
        elif action == 7: # Close Claw
           action_id = "close"
        
        #print("Action_id="+str(action_id)+",IncrementVector===>"+str(increment_vector))

        if action_id == "move":
            # We tell shadow_tc the action to perform
            # We dont change the RPY, therefore it will always be zero
            
            self.move_tip(  x=increment_vector.x,
                            y=increment_vector.y,
                            z=increment_vector.z)
        
        elif  action_id == "open":
            self.open_hand()
        elif action_id == "close":
            self.close_hand()
            
        #print("END Set Action ==>"+str(action)+",action_id="+str(action_id)+",IncrementVector===>"+str(increment_vector))

    def _get_obs(self):
        """
        Here we define what sensor data defines our robots observations
        To know which Variables we have access to, we need to read the
        shadow_tcEnv API DOCS.
        :return: observation
        """
        #print("Start Get Observation ==>")
        
        tcp_pose = self.get_tip_pose()
        
        # We dont add it to the observations because is not part of the robot
        self.ball_pose = self.get_ball_pose()
        
        # We activate the Finguer collision detection
        self.finger_collided_dict = self.get_fingers_colision(object_collision_name="cricket_ball__link")
        f1_collided = self.finger_collided_dict["f1"]
        f2_collided = self.finger_collided_dict["f2"]
        f3_collided = self.finger_collided_dict["f3"]
        
        
        observation = [ round(tcp_pose.position.x,self.dec_obs),
                        round(tcp_pose.position.y,self.dec_obs),
                        round(tcp_pose.position.z,self.dec_obs),
                        int(f1_collided),
                        int(f2_collided),
                        int(f3_collided)
                        ]
                        
        #print("Observations ==>"+str(observation))
        #print("END Get Observation ==>")

        return observation
        

    def _is_done(self, observations):
        """
        We consider the episode done if:
        1) The shadow_tc TCP is outside the workspace.
        2) The TCP to block distance is lower than a threshold ( it got to the place )
           and the the collisions in the figuers are true.
        """
        tcp_pos = Vector3()
        tcp_pos.x = observations[0]
        tcp_pos.y = observations[1]
        tcp_pos.z = observations[2]
        
        # We check if all three finguers have collided with the ball
        finguers_collided = observations[3] and observations[4] and observations[5]
        
        bool_is_inside_workspace = self.is_inside_workspace(tcp_pos)
        
        
        has_reached_the_ball = self.reached_ball(  tcp_pos,
                                                    self.ball_pose.position,
                                                    self.acceptable_distance_to_ball,
                                                    finguers_collided)
        
        done = has_reached_the_ball or not(bool_is_inside_workspace)
        
        #print("#### IS DONE ? ####")
        #print("Not bool_is_inside_workspace ?="+str(not(bool_is_inside_workspace)))
        #print("has_reached_the_ball ?="+str(has_reached_the_ball))
        #print("done ?="+str(done))
        #print("#### #### ####")
        
        return done

    def _compute_reward(self, observations, done):
        """
        We Base the rewards in if its done or not and we base it on
        if the distance to the ball has increased or not.
        :return:
        """

        tcp_pos = Vector3()
        tcp_pos.x = observations[0]
        tcp_pos.y = observations[1]
        tcp_pos.z = observations[2]
        # We check if all three finguers have collided with the ball
        finguers_collided = observations[3] and observations[4] and observations[5]
        
        distance_from_ball = self.get_distance_from_point(self.ball_pose.position, tcp_pos)
        
        distance_difference =  distance_from_ball - self.previous_distance_from_ball


        if not done:
            
            # If there has been a decrease in the distance to the desired point, we reward it
            if distance_difference < 0.0:
                rospy.logerr("NOT ERROR: DECREASE IN DISTANCE GOOD")
                reward = self.closer_to_block_reward
            else:
                rospy.logerr("NOT ERROR: ENCREASE IN DISTANCE BAD")
                #reward = -1*self.closer_to_block_reward
                reward = 0.0

        else:
            
            has_reached_the_ball = self.reached_ball(   tcp_pos,
                                                        self.ball_pose.position,
                                                        self.acceptable_distance_to_ball,
                                                        finguers_collided)
        
            if has_reached_the_ball:
                reward = self.done_reward
            else:
                reward = -1*self.done_reward


        self.previous_distance_from_ball = distance_from_ball


        #print("reward=" + str(reward))
        self.cumulated_reward += reward
        #print("Cumulated_reward=" + str(self.cumulated_reward))
        self.cumulated_steps += 1
        #print("Cumulated_steps=" + str(self.cumulated_steps))

        return reward


    # Internal TaskEnv Methods

    def reached_ball(self,tcp_position, ball_position, minimum_distance, finguers_collided):
        """
        Return true if the distance from TCP position to the ball position is 
        lower than the minimum_distance and all three finguers are touching the ball.
        """
        
        distance_from_ball = self.get_distance_from_point(tcp_position, ball_position)
        
        distance_to_ball_ok = distance_from_ball < minimum_distance
        
        reached_ball_b = distance_to_ball_ok and finguers_collided
        
        #print("###### REACHED BLOCK ? ######")
        #print("distance_from_ball==>"+str(distance_from_ball))
        #print("distance_to_ball_ok==>"+str(distance_to_ball_ok))
        #print("reached_ball_b==>"+str(reached_ball_b))
        #print("finguers_collided==>"+str(finguers_collided))
        #print("############")
        
        return reached_ball_b

        
    def get_distance_from_point(self, pstart, p_end):
        """
        Given a Vector3 Object, get distance from current position
        :param p_end:
        :return:
        """
        a = numpy.array((pstart.x, pstart.y, pstart.z))
        b = numpy.array((p_end.x, p_end.y, p_end.z))
    
        distance = numpy.linalg.norm(a - b)
    
        return distance
    

    def is_inside_workspace(self,current_position):
        """
        Check if the shadow_tc is inside the Workspace defined
        """
        is_inside = False

        #print("##### INSIDE WORK SPACE? #######")
        #print("XYZ current_position"+str(current_position))
        #print("work_space_x_max"+str(self.work_space_x_max)+",work_space_x_min="+str(self.work_space_x_min))
        #print("work_space_y_max"+str(self.work_space_y_max)+",work_space_y_min="+str(self.work_space_y_min))
        #print("work_space_z_max"+str(self.work_space_z_max)+",work_space_z_min="+str(self.work_space_z_min))
        #print("############")

        if current_position.x > self.work_space_x_min and current_position.x <= self.work_space_x_max:
            if current_position.y > self.work_space_y_min and current_position.y <= self.work_space_y_max:
                if current_position.z > self.work_space_z_min and current_position.z <= self.work_space_z_max:
                    is_inside = True
        
        return is_inside
        
    

