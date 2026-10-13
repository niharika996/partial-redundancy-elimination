// Block B1
if flag > 0 goto L_split_1

// Block B_split_1
L_split_1:
t_u_add_v = u + v
goto L_MERGE

// Block B2
t_u_add_v = u + v
temp = t_u_add_v
goto L_MERGE

// Block B3
L_OTHER:
t_u_add_v = u + v
x = 100
goto L_MERGE

// Block B4
L_MERGE:
res = t_u_add_v
return res

