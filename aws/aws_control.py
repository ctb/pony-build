import time
import boto
import paramiko
from secret import aws_id, aws_key
from boto.ec2.connection import EC2Connection
import sys
import socket

def connect_ec2():
    conn = EC2Connection(aws_id, aws_key)
    return conn

def start_instance(conn):
    image = conn.get_image('ami-1d729474')
    print image.location

    reservation = image.run(key_name='default', placement='us-east-1c')
    instance = reservation.instances[0]

    return instance

def get_running_instance(conn):
    reslist = conn.get_all_instances()
    for r in reslist:
        for instance in r.instances:
            if instance.state == 'running':
                return instance

    return None

def poll_for_instance(conn):
    inst = get_running_instance(conn)
    while not inst:
        print 'refresh'
        time.sleep(0.5)
        inst = get_running_instance(conn)

    print 'found:', inst

def attach_volume(conn, instance):
    volume_id = 'vol-7396571a'
    conn.attach_volume(volume_id, instance.id, '/dev/sdh')

def connect_ssh(instance):
    hostname = instance.public_dns_name
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, username='root',
                key_filename='/Users/t/.aws/default.pem')
    return ssh

##    stdin, stdout, stderr = ssh.exec_command('ls /bin')
    
def mount(ssh):
    _, stdout, stderr = ssh.exec_command('mount /dev/sdh /mnt')
    print stdout.readlines()

    _, stdout, stderr = ssh.exec_command('ls /mnt')
    print stdout.readlines()

def install_stuff(ssh):
    _, stdout, stderr = ssh.exec_command('apt-get update')
    print stdout.readlines()

    _, stdout, stderr = ssh.exec_command('apt-get -y install git-core')
    print stdout.readlines()

    _, stdout, stderr = ssh.exec_command('git clone git://github.com/ctb/pony-build.git')
    print stdout.readlines()

    _, stdout, stderr = ssh.exec_command('cd pony-build && git pull origin rpc')
    print stdout.readlines()

    _, stdout, stderr = ssh.exec_command('cd pony-build && python rpc_server.py >& rpc_server.out &')
    print stdout.readlines()

def go(startup=True, retry_ssh_connect=5):
    conn = connect_ec2()
    instance = get_running_instance(conn)

    print 'running instance?', instance

    if not instance and startup:
        instance = start_instance(conn)

        while instance.update() != 'running':
            print instance, instance.update()
            time.sleep(1)
    
    ssh = None
    if instance:
        print 'instance: %s (%s)' % (instance, instance.update())

        for i in range(retry_ssh_connect):
            try:
                ssh = connect_ssh(instance)
                break
            except socket.error:
                print 'waiting for sshd connection'

            time.sleep(1)

    return ssh

if __name__ == '__main__':
    args = sys.argv[1:]

    if len(args) == 0:
        print 'commands: connect, shutdown_all, start'
        sys.exit(0)

    assert len(args) == 1
    command = args[0]

    if command == 'connect':
        ssh = go(startup=False)
        print ssh
    elif command == 'shutdown_all':
        conn = connect_ec2()
        
        instance = get_running_instance(conn)
        while instance:
            print 'shutting down', instance
            instance.stop()
            instance = get_running_instance(conn)
            
    elif command == 'start':
        ssh = go()
        print ssh
