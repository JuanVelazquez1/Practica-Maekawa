from copy import deepcopy
from datetime import datetime, timedelta
from math import ceil, sqrt
from threading import Event, Thread, Timer
import utils
import config

class NodeSend(Thread):
    def __init__(self, node):
        Thread.__init__(self)
        self.node = node
        self.client_sockets = [utils.create_client_socket() for i in range(config.numNodes)]
    
    def build_connection(self):
        for i in range(config.numNodes):
            self.client_sockets[i].connect(('localhost',config.port+i))
    
    def run(self):
        self.update()

    """ Request-Enter-Exit cycle
        
        Request: requests for entering the critical section (CS)
        Enter: enters into the critical section when it gets enough votes
        Exit: exits the critial section
    """
    def update(self):
        while True:
            self.node.signal_request_cs.wait()
            self.node.request_cs(datetime.now())
            self.node.signal_enter_cs.wait()
            self.node.enter_cs(datetime.now())
            self.node.signal_exit_cs.wait()
            self.node.exit_cs(datetime.now())

    def send_message(self, msg, dest, multicast=False):
        if not multicast:
            self.node.lamport_ts += 1
            msg.set_ts(self.node.lamport_ts)
        assert dest == msg.dest
        self.client_sockets[dest].sendall(bytes(msg.to_json(),encoding='utf-8'))


    def multicast(self, msg, group):
        self.node.lamport_ts += 1
        msg.set_ts(self.node.lamport_ts)
        for dest in group:
            new_msg = deepcopy(msg)
            new_msg.set_dest(dest)
            assert new_msg.dest == dest
            assert new_msg.ts == msg.ts
            self.send_message(new_msg, dest, True)