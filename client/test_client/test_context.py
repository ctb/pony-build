import os
from pony_client import Context, BaseCommand, do, TempDirectoryContext
import pony_client

class StubCommand(BaseCommand):
    command_name = 'test command'
    def __init__(self):
        BaseCommand.__init__(self, [])

    def run(self, context):
        self.output = 'some output'
        self.errout = 'some errout'
        self.duration = 0.

class SuccessfulCommand(StubCommand):
    command_type = 'forced_success'
    def run(self, context):
        self.status = 0

class FailedCommand(StubCommand):
    command_type = 'forced_failure'
    def run(self, context):
        self.status = -1
        
class ExceptedCommand(StubCommand):
    command_type = 'forced_exception'
    def run(self, context):
        raise Exception("I suck")

class FailedContextInit(Context):
    def __init__(self, *args, **kwargs):
        Context.__init__(self, *args, **kwargs)
    def initialize(self):
        Context.initialize(self)
        raise Exception("I suck too")

def test_context_failure():
    c = FailedContextInit()

    (client_info, _, _) = do('foo', [ SuccessfulCommand() ], context=c)
    assert not client_info['success']

def test_failed_command():
    c = Context()

    (client_info, _, _) = do('foo', [ FailedCommand() ], context=c)
    assert not client_info['success']

def test_exception_command():
    c = Context()

    (client_info, _, _) = do('foo', [ ExceptedCommand() ], context=c)
    assert not client_info['success']

def test_misc_TempDirectoryContext_things():

    c = TempDirectoryContext()

    c.initialize()
    # test for temp folder creation
    assert os.path.exists(c.tempdir)

    c.finish()
    # test for temp folder proper deletion
    assert not os.path.exists(c.tempdir)
