import sys
import atexit

# todo: make written-to stream passable

class Plan(object):
  def __init__(self, plan, param=None,out=sys.stdout):
    self.counter = 0
    self.expected_tests = None
    self.ended = False
    self.out = out

    if isinstance(plan, int):
      self.expected_tests = plan
      self.out.write("1..%u\n" % self.expected_tests)
    elif plan == "no_plan" or plan == None: 1
    elif plan == "skip_all":
      self.out.write("1..0 # skip %s\n" % param)
      raise SystemExit(0) # ??? this is what T::B does, but sucks
    else:
      raise TestBadPlan(plan)

  def increment_counter(self):
    self.counter += 1

  def __del__(self):
    if self.ended: return
    self.ended = True
    if self.expected_tests is None:
      self.out.write("1..%u\n" % self.counter)
    elif self.counter != self.expected_tests:
      self.out.write("# Looks like you planned %u tests but ran %u.\n" \
        % (self.expected_tests, self.counter))

class Builder(object):
  global_defaults = {
    "_plan":    None,
    "current":  1,
    "has_plan": False,
    "out": sys.stdout
  }
  global_test_builder = global_defaults.copy()

  def __init__(self, plan=None, plan_param=None, out=sys.stdout):
    self.__dict__ = self.global_test_builder
    if plan: self.set_plan(plan, plan_param)
    self.out = out

  @classmethod # XXX: why did this fail?
  def create(cls, plan=None, plan_param=None, out=sys.stdout):
    # self = new.instance(cls) # ? this sucks, too
    self = Builder()
    self.__dict__  = self.global_defaults.copy()
    self.out = out
    if plan: self.set_plan(plan, plan_param)
    return self

  def set_plan(self, plan, plan_param=None):
    if self.get_plan(): raise TestPlannedAlready(plan, plan_param)
    self._plan = Plan(plan, plan_param,out=self.out)    
    atexit.register(self._plan.__del__)

  def get_plan(self): return self._plan
 
  def ok(self, is_ok, desc=None, skip=None, todo=None):
    self.get_plan().increment_counter()
    if is_ok: report = "ok" 
    else:     report = "not ok"

    self.out.write("%s %u" % (report, self.current))

    if desc: self.out.write(" - %s" % desc)
    if skip: self.out.write(" # SKIP %s" % skip)
    if todo: self.out.write(" # TODO %s" % todo)

    self.out.write("\n")
    self.current += 1

  def reset(self):
    self.__dict__.clear()
    for key in self.global_defaults.iterkeys():
      self.__dict__[key] = self.global_defaults[key]

class TestPlannedAlready(Exception):
  def __init__(self, plan, param=None):
    self.plan  = plan
    self.param = param
  def __str__(self):
    return "tried to plan twice; second plan: %s, %s" % self.plan, self.param

class TestWithoutPlan(Exception):
  def __str__(self):
    return "tried running tests without a plan"

class TestBadPlan(Exception):
  def __init__(self, plan):
    self.plan = plan
  def __str__(self):
    return "didn't understand plan '%s'" % self.plan
