// Block B1
if cond > 0 goto L_THEN

// Block B2
t_a_add_b = a + b
x = t_a_add_b
goto L_MERGE

// Block B3
L_THEN:
t_a_add_b = a + b
c = 10
goto L_MERGE

// Block B4
L_MERGE:
y = t_a_add_b
return y

