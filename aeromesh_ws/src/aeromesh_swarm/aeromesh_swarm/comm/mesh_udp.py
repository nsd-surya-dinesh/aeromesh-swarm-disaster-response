"""Mesh UDP node — optional broadcast helper."""

class MeshUDPNode:
    def __init__(self, port=5005):
        self.port = port

    def send(self, packet):
        print("[MESH] UDP send", len(packet))

    def receive_loop(self, callback):
        print("[MESH] UDP receive loop started")
