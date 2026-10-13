// Benchmark 1: Classic Partial Redundancy
// Expression 'a + b' is computed on the ELSE branch (B2) and in the MERGE block (B4).
// PRE hoists/inserts 'a + b' into the THEN branch (B3) so that 'a + b' in MERGE is fully redundant.

if cond > 0 goto L_THEN
x = a + b
goto L_MERGE

L_THEN:
c = 10
goto L_MERGE

L_MERGE:
y = a + b
return y
