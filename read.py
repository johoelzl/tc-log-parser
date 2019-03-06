#!/usr/bin/python3
import re
import collections

log_regex = re.compile(r"""
  (\[class_instances\]\ \((?P<depth>\d+)\)
    \ \?x_(?P<mvar>\d+)\ (?P<locals>[^:]*):\ (?P<type>.*)\ :=\ (?P<val>.*)) |
  (\[type_context.tmp_vars\]\ (?P<cmd1>(assign)|(unassign))\ \?x_(?P<mvar2>\d+)\ :=\ (?P<val2>.*)) |
  (\[type_context.tmp_vars\]\ (?P<cmd2>(push_scope)|(pop_scope)),\ trail_sz:\ (?P<sz>\d+)) |
  (?P<fail>failed\ is_def_eq)""",
  re.DOTALL | re.VERBOSE)

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

class Instance:
  """ Instance assignment (with successfull def_eq) """
  def __init__(self, scope, cnt, d, m, l, t, v):
    self.scope = scope
    self.cnt = cnt
    self.depth = d
    self.mvar = m
    self.locals = l
    self.type = t
    self.val = v

  def print(self):
    print("% 5i  (% 2i)  ?x_%i : %s := %s" % (self.cnt, self.depth, self.mvar, self.type, self.val))

class Scope:
  """ Search scope per instance """
  def __init__(self, parent):
    self.parent = parent
    if self.parent:
      assert(parent.applies)
      self.instance = parent.applies[-1]
      self.parent.subscopes.append(self)
    else:
      self.instance = None
    self.applies = []
    self.subscopes = []
    self.mvars = collections.OrderedDict()

  def print(self):
    if self.instance:
      self.instance.print()
    print("     subscopes ", len(self.subscopes))

class ContextParser(Parser):
  def __init__(self):
    self.apply_cnt = 0
    self.scope = Scope(None)

  def push_scope(self, sz):
    self.scope = Scope(self.scope)

  def pop_scope(self, sz):
    self.scope = self.scope.parent

  def assign(self, mvar, val):
    self.scope.mvars[mvar] = val

  def unassign(self, mvar, val):
    if mvar in self.scope.mvars:
      del self.scope.mvars[mvar]
    else:
      # print("cannot unnassign %i" % mvar)
      pass

  def apply_instance(self, d, m, l, t, v):
    self.apply_cnt += 1
    self.scope.applies.append(Instance(self.scope, self.apply_cnt, d, m, l, t, v))

  def apply_failed(self):
    self.scope.applies.pop()
    self.apply_cnt -= 1

  def finished(self):
    scope = self.scope
    scopes = []
    while scope and scope.parent:
      scopes.insert(0, scope)
      scope = scope.parent

    print ("scopes (choice points, tc depth): %i" % len(scopes))
    print ("last scope:")
    for s in scopes:
      s.print()

f = open("WRONG")
p = ContextParser()
p.parse(f)
