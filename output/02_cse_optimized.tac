// Block B1
t_x_mul_y = x * y
t1 = t_x_mul_y
if val > 5 goto L_PATH1

// Block B2
a = 1
goto L_JOIN

// Block B3
L_PATH1:
b = 2
goto L_JOIN

// Block B4
L_JOIN:
t2 = t_x_mul_y
result = 1 + t2
return result

