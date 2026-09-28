import os, sys
log = sys.argv[1]; cmd = sys.argv[2:]
if os.fork() > 0:
    sys.exit(0)                      # parent exits immediately -> tool sees clean exit
os.setsid()
if os.fork() > 0:
    os._exit(0)                      # ensure we're not a session leader
dn = os.open(os.devnull, os.O_RDONLY); os.dup2(dn, 0)
fd = os.open(log, os.O_WRONLY|os.O_CREAT|os.O_APPEND, 0o644)
os.dup2(fd, 1); os.dup2(fd, 2)
os.execvp(cmd[0], cmd)
