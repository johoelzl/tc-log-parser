import linear_algebra.matrix
import linear_algebra.dimension
import algebra.pi_instances
import linear_algebra.basic
import topology.instances.nnreal

import analysis.normed_space.basic

class test (α : Type*)

class mark (b : bool)

instance test_init (α : Type*) [decidable_eq α] [mark ff] :
  test α :=
test.mk _

instance mark_tt : mark tt := mark.mk _

set_option trace.class_instances true
set_option pp.proofs true

example {α : Type} [fintype α] [discrete_field α] (n : ℕ) (A : finset (fin n → α)) :
  test (fin n) :=
begin
  tactic.trace "pre",
  apply_instance
end

/-
instance t₁ (α : Type*) (x : α) (A : finset α) [decidable_eq α] [inhabited empty] :
  test {x // x ∈ A} :=
test.mk _


example {α : Type} [fintype α] [discrete_field α] (n : ℕ) (A : finset (fin n → α)) :
  normed_group (Π (i : {x // x ∈ A}), (λ (a : {x // x ∈ A}), α) i) :=
-- by apply_instance
-/
