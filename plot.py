import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.pyplot import *

training = pd.read_csv("training.txt")
fig, ax = subplots()
training.plot(kind='scatter',x='cadence',y='power3',color="blue", ax=ax)
plt.show()