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
    p_n = 1
    for (n, l) in enumerate(f.readlines()):
      if l.startswith("  "):
        p += " " + l.strip()
        continue

      if p != '':
        self.parse_paragraph(p_n, p)

      p = l.strip()
      p_n = n + 1

    if p != '':
      self.parse_paragraph(p_n, p)
    self.finished()

  def parse_paragraph(self, l, p):
    m = log_regex.fullmatch(p)
    if not m:
      print("Unkown log message:", repr(p))
      return

    d = m.groupdict()
    if d['depth']:
      self.apply_instance(l,
        int(d["depth"]), int(d["mvar"]), d["locals"].split(),
        d["type"].strip(), d["val"].strip())
    elif d["cmd1"] == "assign":
      self.assign(l, int(d["mvar2"]), d["val2"].strip())
    elif d["cmd1"] == "unassign":
      self.unassign(l, int(d["mvar2"]), d["val2"].strip())
    elif d["cmd2"] == "push_scope":
      self.push_scope(l, int(d["sz"]))
    elif d["cmd2"] == "pop_scope":
      self.pop_scope(l, int(d["sz"]))
    elif d["fail"]:
      self.apply_failed(l)

  def finished(self):
    pass

  def apply_instance(self, line, depth, mvar, locals, type, val):
    pass

  def apply_failed(self, line):
    pass

  def assign(self, line, mvar, val):
    pass

  def unassign(self, line, mvar, val):
    pass

  def push_scope(self, line, sz):
    pass

  def pop_scope(self, line, sz):
    pass

class MetaVariable:
  active_mvars = dict()

  def __init__(self, parent, idx):
    self.parent = parent
    self.idx = idx

    self.type = None
    self.depth = None
    self.locals = None

    self.active_instance = None
    self.active_run = None
    self.runs = []

  def set(self, instance):
    if not self.active_run:
      self.active_run = []
      self.runs.append((self.active_run, None))
    self.active_run.append(instance)

    self.active_instance = instance

    if self.depth is None:
      self.depth = instance.depth
    else:
      assert(self.depth == instance.depth)
    if self.type is None:
      self.type = instance.type
    else:
      assert(self.type == instance.type)
    if self.locals is None:
      self.locals = instance.locals
    else:
      assert(self.locals == instance.locals)

  def backtrack(self, i):
    self.deactivate_instance(Backtracking(i))
    if self.runs:
      self.runs[-1] = (self.runs[-1][0], i)
    self.active_run = None

  def deactivate_instance(self, reason):
    if self.active_instance:
      self.active_instance.deactivate(reason)
      self.active_instance = None

  def deactivate(self, reason):
    self.deactivate_instance(reason)
    del MetaVariable.active_mvars[self.idx]

  def activate(self):
    assert(self.idx not in MetaVariable.active_mvars)
    MetaVariable.active_mvars[self.idx] = self

  def non_failed_runs(self):
    for (l, r) in self.runs:
      pass

  def print_tree(self, prefix="", depth=3):
    for (l, r) in self.runs:
      failed = True
      for i in l:
        if not (i.failure_reason and i.failure_reason.is_def_eq()):
          i.print_tree(prefix, depth)
          failed = False
      if failed:
        if l:
          line = l[0].line
        else:
          line = 0
        print("%6i: %s failed or empty run in %s" % (line, prefix, self.idx))
      if r is not None:
        print("%6i: %s backtracking %s by %s" % (r.line, prefix, self.idx, r))

  def __str__(self):
    if self.type:
      return "[?x_%i : %s]" % (self.idx, self.type)
    else:
      return "?x_%i" % self.idx

  def collect(self, instantiations):
    for (l, r) in self.runs:
      for i in l:
        i.collect(instantiations)

MetaVariable.active_mvars[0] = MetaVariable(None, 0)

class Failure:
  def is_def_eq(self):
    return False

class DefEqFailure(Failure):
  def __init__(self, line):
    self.line = line

  def is_def_eq(self):
    return True

  def __str__(self):
    return "DefEq@%i" % self.line

class Replacement(Failure):
  def __init__(self, i):
    self.instance = i

  def __str__(self):
    return "Replacement " + str(self.instance)

class Backtracking(Failure):
  def __init__(self, i):
    self.instance = i

  def __str__(self):
    return "Backtracking " + str(self.instance)

class Instantiation:
  def __init__(self, line, depth, target, locals, type, value):
    self.line = line
    self.target = target
    self.depth = depth
    self.locals = locals
    self.type = type
    self.value = value

    self.failure_reason = None

    const_name = self.value.split()[0]
    if const_name.startswith("@"):
      const_name = const_name[1:]
    self.const_name = const_name

    self.mvars = [MetaVariable(self, int (i))
      for i in mvar_regex.findall(self.value)]

  def activate(self):
    self.target.set(self)
    for m in self.mvars:
      m.activate()

  def deactivate(self, reason):
    self.failure_reason = reason
    for m in self.mvars:
      m.deactivate(reason)

  def collect(self, instantiations):
    if self.failure_reason and self.failure_reason.is_def_eq():
      return

    i = instantiations.setdefault(self.const_name, 0)
    instantiations[self.const_name] = i + 1

    for m in self.mvars:
      m.collect(instantiations)

  def print_tree(self, prefix="", depth=3):
    print("%6i: %s ?x_%i := %s %s" %
      (self.line, prefix, self.target.idx, self.const_name,
        ", ".join([str(m) for m in self.mvars])))

    if depth == 0: return
    for m in self.mvars:
      m.print_tree(prefix + "  ", depth - 1)

  def __str__(self):
    return "?x_%i := %s (%s)" % (self.target.idx, self.const_name, self.failure_reason)

class ContextParser(Parser):
  def __init__(self):
    self.last_instance = None

  def apply_instance(self, ln, d, m, l, t, v):
    m = MetaVariable.active_mvars[m]
    i = Instantiation(ln, d, m, l, t, v)
    self.last_instance = i

    # add backtracking information
    if m.active_instance:
      m.deactivate_instance(Replacement(i))
      while m.parent:
        parent = m.parent
        pos = parent.mvars.index(m)
        for sibling in parent.mvars[pos + 1:]:
          sibling.backtrack(i)
        m = parent.target

    # add active mvars
    i.activate()

  def apply_failed(self, ln):
    self.last_instance.target.deactivate_instance(DefEqFailure(ln))
    self.last_instance = None

def read(name):
  f = open(name)
  p = ContextParser()
  p.parse(f)
  return p

def print_tree(depth=4):
  print("tree:")
  m = MetaVariable.active_mvars[0]
  m.print_tree(depth = depth)
  print()

def instantiation_histogram():
  d = dict()
  MetaVariable.active_mvars[116].collect(d)
  i = list(d.items())
  i.sort(key = lambda p: p[1])
  for (n, c) in i:
    print ("%5i  %s" % (c, n))

if __name__ == "__main__":
  if len(sys.argv) > 1:
    name = sys.argv[1]
  else:
    name = "WRONG"
  p = read(name)

  # print_tree()
  instantiation_histogram()
