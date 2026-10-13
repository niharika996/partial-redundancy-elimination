// Benchmark 3: Loop-Invariant Code Motion (LICM Subsumption)
// The expression 'base * factor' is computed inside the loop body (L_LOOP).
// Since 'base' and 'factor' are invariant throughout the loop, PRE hoists
// 'base * factor' to the loop preheader so it is evaluated only once.

i = 0
n = 100

L_LOOP:
val = base * factor
i = i + 1
if i < n goto L_LOOP

return val
