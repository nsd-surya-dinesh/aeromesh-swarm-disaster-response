import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/surya/projects/aeromesh-swarm-disaster-response/aeromesh_ws/install/aeromesh_swarm'
