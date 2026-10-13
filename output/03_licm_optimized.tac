// Block B1
t_base_mul_factor = base * factor
i = 0
n = 100

// Block B2
L_LOOP:
val = t_base_mul_factor
i = 1 + i
if i < n goto L_split_1

// Block B_split_1
L_split_1:
goto L_LOOP

// Block B3
return val

