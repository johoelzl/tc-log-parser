How much instances does Lean find to proof:
  decidable_eq (fin n)?

Answer 12:

1 * fin.decidable_eq
1 * eq.decidable ← fin.decidable_linear_order
10 * decidable_eq_of_decidable_le:
    ((semilattice_inf | semilattice_sup) *
        (lattice_of_dlo | (distrib_lattice ← distrib_lattice_of_dlo)) +
      (linorder ← linorder_of_dlo)) *
    (fin.decidable_le | has_le.le.decidable ← fin.decidable_linear_order)

Why is this a problem?

We have a type class problem of the shape:

   C [t1 : decdiable_eq (fin n)] [t2 : expensive] [t3 : fails]

where t2 is a instance which may take a couple of seconds, and t3 fails.
Lean doesn't realize that t3 is independent of t2 and t1, so it repeats the entire search 12 times.



