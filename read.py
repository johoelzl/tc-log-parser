#!/usr/bin/python3
import re
import collections
import sys

log_regex = re.compile(r"""
  (\[class_instances\]\ \((?P<depth>\d+)\)
    \ \?x_(?P<mvar>\d+)\ (?P<locals>[^:]*):\ (?P<type>.*)\ :=\ (?P<val>.*)) |
  (\[type_context.tmp_vars\]\ (?P<cmd1>(assign)|(unassign))\ \?x_(?P<mvar2>\d+)\ :=\ (?P<val2>.*)) |
  (\[type_context.tmp_vars\]\ (?P<cmd2>(push_scope)|(pop_scope)),\ trail_sz:\ (?P<sz>\d+)) |
  (?P<fail>failed\ is_def_eq)""",
  re.DOTALL | re.VERBOSE)

mvar_regex = re.compile(r"\?x_(\d+)")

class Parser:
  def parse(self, f):
    p = ""
    for l in f.readlines():
      if l:
        if l.startswith("  "):
          p += " " + l.strip()
        else:
          if p != '':
            self.parse_paragraph(p)
          p = l.strip()
      else:
        p = l.strip()
    if p != '':
      self.parse_paragraph(p)
    self.finished()

  def parse_paragraph(self, p):
    m = log_regex.fullmatch(p)
    if not m:
      print("Unkown log message:", repr(p))
      return

    d = m.groupdict()
    if d['depth']:
      self.apply_instance(int(d["depth"]), int(d["mvar"]), d["locals"].split(),
        d["type"].strip(), d["val"].strip())
    elif d["cmd1"] == "assign":
      self.assign(int(d["mvar2"]), d["val2"].strip())
    elif d["cmd1"] == "unassign":
      self.unassign(int(d["mvar2"]), d["val2"].strip())
    elif d["cmd2"] == "push_scope":
      self.push_scope(int(d["sz"]))
    elif d["cmd2"] == "pop_scope":
      self.pop_scope(int(d["sz"]))
    elif d["fail"]:
      self.apply_failed()

  def finished(self):
    pass

  def apply_instance(self, depth, mvar, locals, type, val):
    pass

  def apply_failed(self):
    pass

  def assign(self, mvar, val):
    pass

  def unassign(self, mvar, val):
    pass

  def push_scope(self, sz):
    pass

  def pop_scope(self, sz):
    pass

class Instantiation:
  def __init__(self, time, target, value, mvars):
    self.time = time
    self.target = target
    self.value = value
    self.mvars = mvars

    self.cost = None

    const_name = self.value.split()[0]
    if const_name.startswith("@"):
      const_name = const_name[1:]
    self.const_name = const_name

  def compute_cost(self):
    if self.cost is not None:
      return self.cost

    cost = 1
    for m in self.mvars:
      cost += m.compute_cost()
    self.cost = cost
    return cost

class MetaVariable:
  all = []
  active = collections.OrderedDict()
  scopes = []

  def __init__(self, number, parent):
    self.number = number
    self.parent = parent
    self.type = None
    self.depth = None
    self.locals = None

    self.instantiations = []
    self.failures = []

    self.cost = None

    assert(not self.parent or number > self.parent.number)

    assert(number not in MetaVariable.active)
    MetaVariable.active[number] = self
    MetaVariable.all.append(self)

  def add_instance(self, time, depth, locals, type, value):
    if self.depth is None:
      self.depth = depth
    else:
      assert(self.depth == depth)
    if self.type is None:
      self.type = type
    else:
      assert(self.type == type)
    if self.locals is None:
      self.locals = locals
    else:
      assert(self.type == type)

    found = None
    for (n, (i, mvars)) in enumerate(MetaVariable.scopes):
      if i.number == self.number:
        found = n

    if found is not None:
      while len(MetaVariable.scopes) > found:
        self.pop_scope()

    mvars = [MetaVariable(int(s), self) for s in mvar_regex.findall(value)]
    self.instantiations.append(Instantiation(time, self, value, mvars))

    MetaVariable.scopes.append((self, mvars))

  def last_instance_failed(self):
    self.failures.append(self.instantiations.pop())
    self.pop_scope()

  def pop_scope(self):
    (n, mvars) = MetaVariable.scopes.pop()
    for m in mvars:
      del MetaVariable.active[m.number]

  def __repr__(self):
    if self.type is None:
      return "?x_%i" % self.number
    else:
      return "?x_%i : %s" % (self.number, self.type)

  def print_instantiations(self, prefix="", costs = [100, 60, 30, 20, 10, 10, 5]):
    next_costs = costs[1:]
    for i in self.instantiations:
      if i.compute_cost() < costs[0]:
        continue

      print("%4i%s ?x_%i [%4i] := %s" % (i.time, prefix, self.number, i.compute_cost(), i.value))

      if next_costs:
        for m in i.mvars:
          m.print_instantiations(prefix + "  ", next_costs)

  def compute_cost(self):
    if self.cost is not None:
      return self.cost

    cost = 0
    for i in self.instantiations:
      cost += i.compute_cost()

    self.cost = cost
    return cost

class ContextParser(Parser):
  def __init__(self):
    self.apply_cnt = 0
    self.root = MetaVariable(0, None)
    self.last_mvar = self.root

  def push_scope(self, sz):
    pass # self.scope = Scope(self.scope)

  def pop_scope(self, sz):
    pass # self.scope = self.scope.parent

  def assign(self, mvar, val):
    pass # self.scope.mvars[mvar] = val

  def unassign(self, mvar, val):
    pass
    # if mvar in self.scope.mvars:
    #   del self.scope.mvars[mvar]
    # else:
    #   print("cannot unnassign %i" % mvar)

  def apply_instance(self, d, m, l, t, v):
    self.apply_cnt += 1
    self.last_mvar = MetaVariable.active[int(m)]
    self.last_mvar.add_instance(self.apply_cnt, d, l, t, v)

    # self.scope.applies.append(Instance(self.scope, self.apply_cnt, d, m, l, t, v))

  def apply_failed(self):
    self.apply_cnt -= 1
    self.last_mvar.last_instance_failed()

  def finished(self):
    self.root.compute_cost()

if len(sys.argv) > 1:
  name = sys.argv[1]
else:
  name = "WRONG"

f = open(name)
p = ContextParser()
p.parse(f)

def print_scope():
  print("scope:")
  for (m, mvars) in MetaVariable.scopes:
    m.print_instantiations(costs=[1000])
  print()

def print_116():
  print("?x_116")
  m = MetaVariable.active[116]
  m.print_instantiations()
  print()

def instantiation_histogram():
  d = dict()
  for m in MetaVariable.all:
    for i in m.instantiations:
      d.setdefault(i.const_name, []).append(i.compute_cost())

  s = list(d.items())
  s.sort(key=lambda t: len(t[1]))
  for (n, l) in s:
    print(n, "  ", len(l), "  ", sum(l))

print_scope()
# print_116()
# instantiation_histogram()


