import numpy as np
import matplotlib.pyplot as plt
import os

#========================================================================================#
'''
@author: Yifan Wang
@date: Aug 2, 2023
WS data reconstruction translated from matlab code
'''
#========================================================================================#

current_directory = os.path.dirname(os.path.abspath(__file__))
file_name = 'WS_memory_data_0801.txt'
file_path = os.path.join(current_directory, file_name)
#print(os.path.abspath(file_name))

with open(file_name, 'r') as f:
    b1 = np.loadtxt(f, dtype=int).T

data_1 = b1[1, :]
data_2 = b1[2, :]

data1 = data_1 % 128
k = None
for i in range(1024):
    if data_1[i] > 127:
        k = i
        break

#print(np.where(data_1 > 127)[0])
end_ind = k - 128 * 7

data_1st_tem = np.zeros((1024, 8), dtype=int)
data_2st_tem = np.zeros((1024, 8), dtype=int)

for i in range(1024):
    data_1_tem = np.binary_repr(data_1[i], width=8)
    l1 = len(data_1_tem)
    data_1st_tem[i] = [int(d) for d in data_1_tem.zfill(8)]
    data_2_tem = np.binary_repr(data_2[i], width=8)
    l1 = len(data_2_tem)
    data_2st_tem[i] = [int(d) for d in data_2_tem.zfill(8)]

data_1st = data_1st_tem[:, 1:7]
data_2st = np.hstack((data_1st_tem[:, 7].reshape(-1, 1), data_2st_tem[:, 0:6]))

gain = 0.05 / 5 * 8.5 * 1
Aout_1st = np.zeros(1024)
Aout_2st = np.zeros(1024)
for i in range(1024):
    Aout_1st[i] = 32 * data_1st[i, 0] + 16 * data_1st[i, 1] + 8 * data_1st[i, 2] + \
        4 * data_1st[i, 3] + 2 * data_1st[i, 4] + data_1st[i, 5]
    Aout_2st[i] = 24 * data_2st[i, 0] + 16 * data_2st[i, 1] + 10 * data_2st[i, 2] + \
        6 * data_2st[i, 3] + 4 * data_2st[i, 4] + 2 * data_2st[i, 5] + data_2st[i, 6]

Aout = Aout_1st - gain * Aout_2st

Aout_ch = np.zeros((8, 128))
Aout_ch_align = np.zeros((8, 128))

for ch in range(1, 9):
    Aout_ch[8 - ch, :] = Aout[(ch - 1) * 128: ch * 128]


for ch in range(1, 9):
    if end_ind == 128:
        Aout_ch_align[ch - 1, :] = Aout_ch[ch - 1, :]
    else:
        Aout_ch_align[ch - 1, :128 - end_ind] = Aout_ch[ch - 1, end_ind:]
        Aout_ch_align[ch - 1, 129 - end_ind - 1: 128] = Aout_ch[ch - 1, :end_ind]

plt.figure()
for i in range(8):
    plt.subplot(8, 1, i + 1)
    plt.plot(Aout_ch_align[i])
    # plt.ylim([0, 2.4])

Aout_8ch = np.zeros(1024)
for i in range(1024):
    Aout_8ch[i] = Aout_ch_align[(i - 1) % 8, (i - 1) // 8]

for i in range(128):
    Aout_8ch[8 * i - 0] = Aout_ch_align[7, i]
    Aout_8ch[8 * i - 1] = Aout_ch_align[6, i]
    Aout_8ch[8 * i - 2] = Aout_ch_align[5, i]
    Aout_8ch[8 * i - 3] = Aout_ch_align[4, i]
    Aout_8ch[8 * i - 4] = Aout_ch_align[3, i]
    Aout_8ch[8 * i - 5] = Aout_ch_align[2, i]
    Aout_8ch[8 * i - 6] = Aout_ch_align[1, i]
    Aout_8ch[8 * i - 7] = Aout_ch_align[0, i]

Aout_8ch_v = -(Aout_8ch - (31.5 - gain * 31.5)) * 1.2 / 32
N = np.arange(1024)
t = N * 1 / 2.56

plt.figure()
plt.plot(t, Aout_8ch_v, linewidth = 0.5 )
plt.ylim([-0.4, -0.1])
plt.xlim([0, 400])
plt.ylabel("Voltage(V)")
plt.xlabel("Time(ns)")
plt.show()

#print("Mean of Aout_8ch_v ", np.mean(Aout_8ch_v))
#print("Variance of Aout_8ch_v ", np.var(Aout_8ch_v))
#print('\n')

# high_pulse_indices = np.where(Aout_8ch_v > -0.22)[0]
highest_values = np.sort((Aout_8ch_v))[-2:]
print("两个pulse的峰值: ", highest_values)