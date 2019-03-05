#!/usr/bin/python3
import re
import collections

inst = re.compile(r"\[class_instances\]\ \((\d+)\)\ \?x_(\d*)\ ([^:]*):\ (.*?):=\ (.*)", re.DOTALL | re.VERBOSE)

class Inst:
  def __init__(self, depth, varname, params, type, value):
    self.parent = None
    self.depth = int(depth)
    self.varname = varname
    self.params = params.split()
    self.type = type
    self.value = value

    self.failed = False
    self.nodes = collections.OrderedDict()

  def set_parent(self, parent):
    self.parent = parent
    if self.parent:
      self.parent.nodes.setdefault(self.varname, []).append(self)

  def is_success(self):
    if self.failed: return False

    for (var, lst) in self.nodes.items():
      for i in lst:
        if i.is_success(): break
      else:
        return False

    return True

  def print_tree(self):
    if self.failed: return

    print("BEGIN (%i) ?x_%s : %s := %s".format(self.depth, self.varname, self.type, self.value))
    for (var, lst) in self.nodes.items():
      for i in lst:
        i.print_tree()
    print("END ?x_%s".format(self.varname))

def paragraph(lines):
  paragraph = ""
  for l in lines:
    if l:
      if l.startswith("  "):
        paragraph += " " + l.strip()
      else:
        yield paragraph
        paragraph = l.strip()
    else:
      paragraph = l.strip()
  yield paragraph

def parser(paragraphs):
  current = None
  for p in paragraphs:
    m = inst.fullmatch(p)
    if m:
      new = Inst(m.group(1), m.group(2), m.group(3), m.group(4), m.group(5))
      while current and current.depth >= new.depth:
        current = current.parent
      new.set_parent(current)
      current = new

    elif p == "failed is_def_eq":
      if current:
        current.failed = True
        current = current.parent
    elif p == "":
      pass
    else:
      raise Exception("unknown", p)

  return current

f = open("WRONG")
p = paragraph(f.readlines())
root = parser(p)
root.print_tree()