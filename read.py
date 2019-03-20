#!/usr/bin/python3
""" Analyse type class instance logs of the Lean theorem prover 3.4.2

The general idea is to perform a backtracking search to find in proofs / terms of the following
form:

  ?x_0 : C p1 ... pn

where ?x_0 is a metavariable, `C` is the name of a class, and `p1` ... `pn` are parameters. Lean
goes through its database of possible instances for each class `C`:
  `I1 : C1 ... -> ... -> Cn ... -> C t1 ... tn`
For this instance to apply `C t1 ... tn` needs to unify with the type `C p1 ... pn`, if they unify
the type class search is continued with `?x_1 : C1 ...` to `?x_n : Cn ...`. If no matching instance
is found, the search backtracks to a previous meta variable to try a different instance.

The log analysed by this program is activated with the following option:
> set_option trace.class_instances true
> set_option pp.proofs true

The program also parses the log when the following option is acitvated:
> set_option trace.type_context.tmp_vars true
But the meta variables instantiations are currently not analysed.

"""
__author__ = "Johannes Hölzl <johannes.hoelzl@posteo.de>"

import re
from collections import OrderedDict
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
  all = {}

  def __init__(self, parent, idx):
    self.parent = parent
    self.idx = idx

    self.type = None
    self.depth = None
    self.locals = None

    l = MetaVariable.all.setdefault(self.idx, [])
    self.generation = len(l)
    l.append(self)

    self.instances = []

  def set(self, instance):
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

    self.instances.append(instance)

  def get_name(self):
    if self.generation == 0:
      return "?x_%i" % self.idx
    else:
      return "?x_%i.%i" % (self.idx, self.generation)

  def __str__(self):
    if self.type:
      return "[%s : %s]" % (self.get_name(), self.type)
    else:
      return self.get_name()

class Instantiation:
  all = []

  def __init__(self, line, depth, target, locals, type, value):
    self.line = line
    self.target = target
    self.depth = depth
    self.locals = locals
    self.type = type
    self.value = value

    self.def_eq_failure = False

    self.backtracked_by = None

    const_name = self.value.split()[0]
    if const_name.startswith("@"):
      const_name = const_name[1:]
    self.const_name = const_name

    self.mvars = [MetaVariable(self, int (i))
      for i in mvar_regex.findall(self.value)]

    Instantiation.all.append(self)

  def print(self):
    print("[% 6i]%s %s" % (self.line, "  " * self.depth, self))

  def __str__(self):
    return "%s := %s" % (self.target, self.value)

class ContextParser(Parser):
  def __init__(self):
    self.instances = OrderedDict()
    self.vars = { 0: MetaVariable(None, 0) }
    self.backtrack_histogram = {}
    self.last = None

  def pop_instance(self):
    elem = self.instances.popitem()
    for m in elem[1].mvars:
      del self.vars[m.idx]
    return elem

  def apply_instance(self, ln, d, m, l, t, v):
    target = self.vars[m]
    new_instance = Instantiation(ln, d, target, l, t, v)

    if target.parent:
      assert(target.parent.target.idx in self.instances)

    if target.idx in self.instances:
      backsteps = 0
      (v, i) = self.pop_instance()
      i.backtracked_by = new_instance
      while v != target.idx:
        (v, i) = self.pop_instance()
        i.backtracked_by = new_instance
        backsteps += 1
      cnt = self.backtrack_histogram.setdefault(backsteps, 0)
      self.backtrack_histogram[backsteps] = cnt + 1

    target.set(new_instance)

    self.instances[target.idx] = new_instance
    for m in new_instance.mvars:
      self.vars[m.idx] = m

    self.last = new_instance

  def apply_failed(self, ln):
    self.last.def_eq_failure = True

def print_instantiation(depth=10):
  for inst in Instantiation.all:
    if inst.def_eq_failure: continue
    if inst.depth > depth: continue
    inst.print()

def print_mvar_tree(mvar, prefix="", depth=1):
  for inst in mvar.instances:
    if inst.def_eq_failure: continue
    print("[% 7i]%s %s" % (inst.line, prefix, inst))
    if depth == 0: continue
    for mv in inst.mvars:
      print_mvar_tree(mv, prefix + "  ", depth - 1)

def read(name):
  f = open(name)
  p = ContextParser()
  p.parse(f)
  return p

if __name__ == "__main__":
  if len(sys.argv) > 1:
    name = sys.argv[1]
  else:
    name = "WRONG"
  p = read(name)

  # i = list(p.backtrack_histogram.items())
  # i.sort(key = lambda p: p[0])
  # print("backtrack count:", i)

  print_instantiation(10)

  # v = MetaVariable.all[0][0]
  # print_mvar_tree(v, depth=6)
