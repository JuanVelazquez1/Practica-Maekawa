from threading import Event, Thread, Timer
from datetime import datetime, timedelta
from nodeServer import NodeServer
from nodeSend import NodeSend
from message import Message
import config
from random import randint
from enum_type import STATE, MSG_TYPE

class Node():
    def __init__(self,id):
        Thread.__init__(self)   # type: ignore
        self.id = id
        self.port = config.port+id
        self.daemon = True
        self.lamport_ts = 0

        # State attribute
        self.node_state = STATE.INIT

        # Attributes as a voter
        self.has_voted = False
        self.voted_request = None
        self.request_queue = []

        # Attributes as a proposer
        self.voting_set = self.create_voting_set()
        self.num_votes_received = 0
        self.has_inquired = False

        # Timestamps for next expected request/exit
        self.time_request_cs = None 
        self.time_exit_cs = None

        # Event signals
        self.signal_request_cs = Event()
        self.signal_request_cs.set()
        self.signal_enter_cs = Event()
        self.signal_exit_cs = Event()

        self.server = NodeServer(self)
        self.server.start()

        self.client = NodeSend(self)    

    def do_connections(self):
        self.client.build_connection()

    # Cases:
    # - The node's state is REQUEST and it got all the votes:
    #       - If it hasn't already made the signal to enter:
    #           - Signal indicating the node could enter 
    # - The node's state is HELD and it has finished its time in the CS:
    #       - If it hasn't already made the signal to exit:
    #           - Signal indicating the node could exit
    # - The node's state is RELEASE and it has finished its time in the CS:
    #       - If it hasn't already made the signal to request:
    #           - Signal indicating the node could request
    def state(self):
        timer = Timer(1, self.state) #Each 1s the function call itself
        timer.start()
        self.curr_time = datetime.now()
        if (self.node_state == STATE.REQUEST and
            self.num_votes_received == len(self.voting_set)):
            if not self.signal_enter_cs.is_set():
                self.signal_enter_cs.set()
        elif (self.node_state == STATE.HELD and 
            self.time_exit_cs <= self.curr_time):
            if not self.signal_exit_cs.is_set():
                self.signal_exit_cs.set()
        elif (self.node_state == STATE.RELEASE and
            self.time_request_cs <= self.curr_time):
            if not self.signal_request_cs.is_set():
                self.signal_request_cs.set()

        #self.wakeupcounter += 1

    # Create voting sets 
    # The voting sets are created manually in order to guarantee 
    # there is no deadlock. We can choose between 3 or 7 nodes 
    def create_voting_set(self):
        voting_set = dict()
        if config.numNodes == 3:
            voting_set = [self.id, (self.id + 1) % config.numNodes]
        elif config.numNodes == 7:
            if self.id == 0:
                voting_set = [0,1,2]
            elif self.id == 1:
                voting_set = [1,3,5]
            elif self.id == 2:
                voting_set = [2,4,5]
            elif self.id == 3:
                voting_set = [3,0,4]
            elif self.id == 4:
                voting_set = [4,1,6]
            elif self.id == 5:
                voting_set = [5,0,6]
            else:
                voting_set = [6,2,3]

        return voting_set


    # Request to enter the Critical Section
    # - Update the node's state
    # - Increase lamport timestamp
    # - Send the request message to the voting set
    def request_cs(self, ts):
        print("Node %i requests access to CS" %self.id)
        self.node_state = STATE.REQUEST
        self.lamport_ts += 1
        request_msg = Message(msg_type=MSG_TYPE.REQUEST, src=self.id)
        self.client.multicast(request_msg, self.voting_set)
        self.signal_request_cs.clear()

    # Enter the Critical Section 
    # - Stay a random time in the CS
    # - Update the node's state
    # - Increase lamport timestamp
    def enter_cs(self, ts):
        print("Node %i accesses CS" %self.id)
        self.time_exit_cs = ts + timedelta(milliseconds=randint(5,10))
        self.node_state = STATE.HELD
        self.lamport_ts += 1
        self.signal_enter_cs.clear()
    
    # Exit the Critical Section
    # - Update the time for the next Critical Section request
    # - Update the node's state
    # - Increase lamport timestamp
    # - Reset the number of votes received to 0
    # - Send the release messageto the voting set
    def exit_cs(self, ts):
        print("Node %i exits CS" %self.id)
        self.time_request_cs = ts + timedelta(milliseconds=randint(5,20))
        self.node_state = STATE.RELEASE
        self.lamport_ts += 1
        self.num_votes_received = 0
        release_msg = Message(msg_type=MSG_TYPE.RELEASE, src=self.id)
        self.client.multicast(release_msg, self.voting_set)
        self.signal_exit_cs.clear()


    def run(self):
        print("Run Node %i with the follows %s"%(self.id,self.voting_set))
        self.client.start()
        self.wakeupcounter = 0
        self.state()