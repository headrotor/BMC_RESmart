import matplotlib
import numpy as np
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

#Adapted for python3 and specific data graphing from
# https://stackoverflow.com/questions/43114508/can-a-pyqt-embedded-matplotlib-graph-be-interactive

import tkinter as tk 
from tkinter import ttk 

class My_GUI:

    def __init__(self,master):
        self.master=master
        master.title("samplegui")
        f = Figure(figsize=(5,5), dpi=100)
        a = f.add_subplot(111)
        a.scatter(np.random.normal(size=100),np.random.normal(size=100),picker=True)
        canvas1=FigureCanvasTkAgg(f,master)
        canvas1.draw()
        canvas1.get_tk_widget().pack(side="top",fill='x',expand=True)
        f.canvas.mpl_connect('pick_event',self.onpick)

        toolbar=NavigationToolbar2Tk(canvas1,master)
        toolbar.update()
        toolbar.pack(side='top',fill='x')

    def onpick(self,event):
        #do stuff
        print("My OnPick Event Worked!")
        return True

root=tk.Tk()
gui=My_GUI(root)
root.mainloop()
