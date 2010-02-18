#! /usr/bin/env python
import time
import boto
import paramiko
from boto.ec2.connection import EC2Connection
import sys
import socket

def connect_ec2():
    from secret import aws_id, aws_key
    return EC2Connection(aws_id, aws_key)

def start_instance(conn):
    image = conn.get_image('ami-1d729474')
    reservation = image.run(key_name='default', placement='us-east-1c')
    instance = reservation.instances[0]

    print 'start instance:', instance

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

def go(startup=True, force_startup=False, retry_ssh_connect=5):
    conn = connect_ec2()

    if force_startup:
        instance = start_instance(conn)

        while instance.update() != 'running':
            print instance, instance.update()
            time.sleep(1)
    else:
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
        print 'instance name:', instance.public_dns_name

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
        print 'commands: connect, connect_or_start, shutdown_all, start_new, list'
        sys.exit(0)

    assert len(args) == 1
    command = args[0]

    if command == 'connect':
        ssh = go(startup=False)
        print 'ssh conn is:', ssh
    elif command == 'shutdown_all':
        conn = connect_ec2()
        
        instance = get_running_instance(conn)
        while instance:
            print 'shutting down', instance
            instance.stop()
            instance = get_running_instance(conn)
    elif command == 'connect_or_start':
        ssh = go()
        print 'ssh conn is:', ssh
    elif command == 'start_new':
        ssh = go(force_startup=True)
        print 'ssh conn is:', ssh
    elif command == 'list':
        conn = connect_ec2()
        reslist = conn.get_all_instances()
        n = 0
        for r in reslist:
            for instance in r.instances:
                if instance.state != 'terminated':
                    print instance, instance.state
                    n += 1

        print '(%d results)' % n
