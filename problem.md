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

tbd
