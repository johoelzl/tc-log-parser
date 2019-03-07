import linear_algebra.matrix
import linear_algebra.dimension
import algebra.pi_instances
import linear_algebra.basic
import topology.instances.nnreal

import analysis.normed_space.basic

section
parameters {α : Type} [fintype α] [discrete_field α] (n : ℕ) (A : finset (fin n → α))
parameter B : matrix {x // x ∈ A} {x // x ∈ A} α

set_option trace.class_instances true
-- set_option trace.type_context.tmp_vars  true
set_option pp.proofs true
#check rank B.to_lin

end