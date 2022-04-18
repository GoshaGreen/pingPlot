# import matplotlib.pyplot as plt


# data = [[16, 17, 16, 16, 17, 17, 17, 17, 17, 17, 17, 16, 16, 17, 17],
# [38, 38, 39, 38, 38, 38, 38, 39, 38, 38, 38, 38, 38, 38, 38],
# [0, 0, 0, 0, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]]

# print('hell o wolf')

# plt.plot(range(len(data[0])), data[0], data[1])
# plt.show()



# import numpy as np
# import matplotlib.pyplot as plt
# from matplotlib.animation import FuncAnimation

# fig, ax = plt.subplots()
# xdata, ydata = [], []
# ln, = plt.plot([], [], 'ro')

# def init():
#     ax.set_xlim(0, 2*np.pi)
#     ax.set_ylim(-1, 1)
#     return ln,

# def update(frame):
#     xdata.append(frame)
#     ydata.append(np.sin(frame))
#     ln.set_data(xdata, ydata)
#     return ln,

# ani = FuncAnimation(fig, update, frames=np.linspace(0, 2*np.pi, 128),
#                     init_func=init, blit=True)
# plt.show()



# import matplotlib.pyplot as plt
# from matplotlib.animation import TimedAnimation

# fig, ax = plt.subplots()
# ln, = plt.plot([], [], 'ro')

# ani = TimedAnimation(fig, ) 



