import select
from threading import Thread
import utils
from message import Message
import json
import heapq
from enum_type import STATE, MSG_TYPE

class NodeServer(Thread):
    def __init__(self, node):
        Thread.__init__(self)
        self.node = node
    
    def run(self):
        self.update()

    def update(self):
        self.connection_list = []
        self.server_socket = utils.create_server_socket(self.node.port)
        self.connection_list.append(self.server_socket)

        while self.node.daemon:
            (read_sockets, write_sockets, error_sockets) = select.select(
                self.connection_list, [], [], 5)
            if not (read_sockets or write_sockets or error_sockets):
                print('NS%i - Timed out'%self.node.id) #force to assert the while condition 
            else:
                for read_socket in read_sockets:
                    if read_socket == self.server_socket:
                        (conn, addr) = read_socket.accept()
                        self.connection_list.append(conn)
                    else:
                        try:
                            msg_stream = read_socket.recvfrom(4096)
                            for msg in msg_stream:
                                try:
                                    ms = json.loads(str(msg,"utf-8"))
                                    self.process_message(ms)
                                except:
                                    None
                        except:
                            read_socket.close()
                            self.connection_list.remove(read_socket)
                            continue
        
        self.server_socket.close()

    # Process the message received from the socket
    def process_message(self, msg):

        self.node.lamport_ts = max(self.node.lamport_ts + 1, msg['ts'])

        if msg['msg_type'] == MSG_TYPE.REQUEST:
            self.on_request(msg)
        elif msg['msg_type'] == MSG_TYPE.GRANT:
            self.on_grant(msg)
        elif msg['msg_type'] == MSG_TYPE.RELEASE:
            self.on_release(msg)
        elif msg['msg_type'] == MSG_TYPE.FAIL:
            self.on_fail(msg)
        elif msg['msg_type'] == MSG_TYPE.INQUIRE:
            self.on_inquire(msg)
        elif msg['msg_type'] == MSG_TYPE.YIELD:
            self.on_yield(msg)

    """ Handle REQUEST
        a. Cache the request if the node is in the critical section currently.
        b. Otherwise, check if the node has voted for a request or not.
                i. If it has, either send an INQUIRE message to the previous 
                    voted requesting node or send a FAIL message to the current 
                    requesting node. (depending on the timestamp and node id order 
                    of the requests)
                ii. Otherwise, vote for current request directly.
    """
    def on_request(self, request_msg):
        print('REQUEST, node %i ha recibido un mensaje de node %i' %(self.node.id, request_msg['src']))
        if self.node.node_state == STATE.HELD:
            heapq.heappush(self.node.request_queue, request_msg)
        else:
            if self.node.has_voted:
                heapq.heappush(self.node.request_queue, request_msg)
                response_msg = Message(src = self.node.id)
                if (request_msg < self.node.voted_request and
                    not self.node.has_inquired):
                    response_msg.set_type(MSG_TYPE.INQUIRE)
                    response_msg.set_dest(self.node.voted_request['src'])
                    self.node.has_inquired = True
                else:
                    response_msg.set_type(MSG_TYPE.FAIL)
                    response_msg.set_dest(request_msg['src'])
                self.node.client.send_message(response_msg, response_msg.dest)
            else:
                self.grant_request(request_msg)
    
    # Vote for a request
    def grant_request(self, request_msg):
        print('GRANT REQUEST, el node %i da acceso a la SC al node %i' %(self.node.id, request_msg['src']))
        grant_msg = Message(msg_type=MSG_TYPE.GRANT,
                            src=self.node.id,
                            dest=request_msg['src'])
        self.node.client.send_message(grant_msg, grant_msg.dest)
        self.node.has_voted = True
        self.node.voted_request = request_msg

    """Handle RELEASE type message
        a. If request priority queue is not empty, pop out the request with
            the highest priority and handle that request.
        b. Otherwise, reset corresponding flags.
    """
    def on_release(self, release_msg=None):
        print('RELEASE, node %i ha salido de la SC' %(self.node.id))
        self.node.has_inquired = False
        if self.node.request_queue:
            next_request = heapq.heappop(self.node.request_queue)
            self.grant_request(next_request)
        else:
            self.node.has_voted = False
            self.node.voted_request = None

    """Handle GRANT type message
        Increase the counter of received votes.
    """
    def on_grant(self, grant_msg):
        self.node.num_votes_received += 1
        print('GRANT, node %i ha recibido un mensaje de node %i, tiene %i votos' %(self.node.id, grant_msg['src'], self.node.num_votes_received))
    
    """Handle FAIL type message"""
    def on_fail(self, fail_msg):
        print('FAIL, node %i ha recibido un mensaje de node %i' %(self.node.id, fail_msg['src']))
        pass

    """Handle INQUIRE type message
        If current node is not in the critical section, send a 
        YIELD message to the inquiring node, indicating it
        would like the inquiring node to revoke the vote.
    """
    def on_inquire(self, inquire_msg):
        print('INQUIRE, node %i ha recibido un mensaje de node %i' %(self.node.id, inquire_msg['src']))
        if self.node.node_state != STATE.HELD:
            self.node.num_votes_received -= 1
            yield_msg = Message(msg_type=MSG_TYPE.YIELD,
                                src=self.node.id,
                                dest=inquire_msg['src'])
            self.node.client.send_message(yield_msg, yield_msg.dest)

    """Handle YIELD type message
        Put the latest voted request back to request queue.
        Then behaves just like receiving a RELEASE message.
    """
    def on_yield(self, yield_msg):
        print('YIELD, node %i ha recibido un mensaje de node %i' %(self.node.id, yield_msg['src']))
        heapq.heappush(self.node.request_queue, self.node.voted_request)
        self.on_release