// Benchmark 4: Critical Edge Splitting Demonstration
// Demonstrates how an edge between a branch and a join/loop header is split
// to allow safe placement of computations without introducing illegal executions.

if flag > 0 goto L_MERGE
temp = u + v
goto L_MERGE

L_OTHER:
x = 100
goto L_MERGE

L_MERGE:
res = u + v
return res
