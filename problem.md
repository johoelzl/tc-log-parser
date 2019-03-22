Question
---

How much instances does Lean find to proof:
  `decidable_eq (fin n)`?

Answer
----

12

```
1 * fin.decidable_eq
1 * eq.decidable ← fin.decidable_linear_order
10 * decidable_eq_of_decidable_le:
    ((semilattice_inf | semilattice_sup) *
        (lattice_of_dlo | (distrib_lattice ← distrib_lattice_of_dlo)) +
      (linorder ← linorder_of_dlo)) *
    (fin.decidable_le | has_le.le.decidable ← fin.decidable_linear_order)
```

Why is this a problem?
---

We have a type class problem of the shape:

```
t : C [t1 : decdiable_eq (fin n)] [t2 : expensive] [t3 : fails]
```

where `t2` is a instance which may take a couple of seconds, and `t3` fails. Lean doesn't realize that `t3` is independent of `t2` and `t1`, so it repeats the entire search 12 times. When searching for a instance Lean does not cache any success/failures, so the search for `t2` and `t3` is repeated 12 times.

So each time a instance is looked up the entire 12 possible cases are enumerated. This problem can occur in any search where a problem of the shape of `t` occurs.


Possible solution
---

When backtracking, ignore the choice points which will result again in the same check. In the example, when `t3` fails we need to look at `t1` and `t2` to check if it instantiated metavariables appearing in the type of `t3`. If they not, the failure of `t3` is independent of `t1` and `t2` and a different outcome wouldn't influence `t3` at all, so we can directly go to the next choice for `t`.

Unfortunately this requires changes to Lean itself.

How does type class search work?
---

The general idea is to perform a backtracking search to find in proofs / terms of the following
form:

```
  ?x_0 : C p1 ... pn
```

where `?x_0` is a metavariable, `C` is the name of a class, and `p1` ... `pn` are parameters.

Lean goes through its database of possible instances for each class `C`, e.g.
```
  I1 : C1 ... → ... → Cn ... → C t1 ... tn
```
For this instance to apply, `C t1 ... tn` needs to unify with the type `C p1 ... pn`, if they unify the type class search is continued with `?x_1 : C1 ...` to `?x_n : Cn ...`. If no matching instance is found, the search backtracks to a previous meta variable to try a different instance.

Now let's assume the instance search constructed the partial term:

```
?x_0 : C ... := I₁ ?x_1 ?x_2
  ?x_1 : D ... := I₂ ?x_3 ?x_4
    ?x_3 : E ... := ...
    ?x_4 : F ... := ...
  ?x_2 : G ....
```

Now we look up instances for `?x_2`. I this succeeds we are finished. If it fails, then Lean will go back to `?x_4` and lookup the next one, if this fails then `?x_3`, `?x_1` and `?x_0`. Each time a meta variable `?x` is instantiated and the next meta variable is filled in, a choice point is created for `?x`. This means that at the time `?x_2` is filled in we have choice points for `?x_0`, `?x_1`, `?x_3`, and `?x_4`. Even if there are no further unifyable instances for these meta variables.

Note that the option `class.instance_max_depth` is the number of possible choice points, i.e. the size of the constructed term.

This is different from the number shown in the `class_instance` log output is the depth of the term, where `?x_0` has 0, `?x_1` and `?x_2` have 1, and `?x_3` and `?x_4` have 2.
