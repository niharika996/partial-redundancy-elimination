// Benchmark 2: Common Subexpression Elimination (Full Redundancy)
// Expression 'x * y' is computed in B1 and recomputed in B3 without x or y being modified.
// LCM detects full redundancy and eliminates the recomputation in B3.

t1 = x * y
if val > 5 goto L_PATH1
a = 1
goto L_JOIN

L_PATH1:
b = 2
goto L_JOIN

L_JOIN:
t2 = x * y
result = t2 + 1
return result
