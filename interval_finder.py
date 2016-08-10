#!/usr/bin/env python
import Tkinter as tk
import tkFileDialog
import tkSimpleDialog
import tkMessageBox
from ScrolledText import ScrolledText
import os, re
import fnmatch
from xml.dom import minidom

DCP_FOLDER = PUT_HERE_PATH_OF_INGESTED_DCPs
TIME_OFFSET = -4  # time offset, in seconds, w.r.t. reel's start
AUTOSUBMIT = 0
SHOW_FTR_ONLY = 1
FPS = 24
CANVAS_WIDTH = 600
CANVAS_HEIGHT = 30
DEBUG = False

# returns a list of all XML files found in `treeroot` (recursively and case-insensitive)
def recursive_glob_ignorecase(treeroot):
    files_list = []
    regex = re.compile("([^\s]+(\.(?i)(xml))$)",re.IGNORECASE)
    for base, dirs, files in os.walk(treeroot):      
        for f in files:
            if base==treeroot:
                fullname=base+f
            else:
                fullname=base+'/'+f
            if (regex.match(fullname)):
                files_list.append(fullname)
    return files_list

# returns a filtered version of `files_list` with all files whose name contains `pattern` and eventually "FTR" (case-insensitive)
def filter_by_pattern(files_list,pattern,show_FTR_only):
    filterd_file_list = []
    if show_FTR_only==1:
        regex = re.compile("^.*"+pattern+".*FTR.*$",re.IGNORECASE)
    else:
        regex = re.compile("^.*"+pattern+".*$",re.IGNORECASE)
    
    for f in files_list:
        if (regex.match(f)):
            filterd_file_list.append(f)
    return filterd_file_list

# converts `frames` into a hh:mm:ss string
def frames_to_hms_string(frames):
    if frames<0:
        frames = 0
    hours = frames/60/60/FPS
    minutes = (frames - hours*60*60*FPS)/60/FPS
    seconds = (frames - hours*60*60*FPS - minutes*60*FPS)/FPS
    return "%02d:%02d:%02d"%(hours,minutes,seconds)

def debug_print(string):
    if DEBUG:
        print(string)
    return

# returns the index of the nearest reel to mid_time and reels' ranges
def find_mid_reel(cum_frm_list):
    '''
    Examples:

    cum_frm_list = [22836, 51927, 76039, 106911]
    mid_time_frm = 53455
    find_mid_reel() returns 2

    cum_frm_list = [22836, 53455, 76039, 106911]
    mid_time_frm = 53455
    find_mid_reel() returns 2 (even if reel_idx is 1, because the nearest reel is the third)

    cum_frm_list = [22836]
    mid_time_frm = 11418
    find_mid_reel() returns -1
    '''
    reels_count = len(cum_frm_list)
    reels_ranges =[ [cum_frm_list[x-1]+1 , cum_frm_list[x]] for x in range(reels_count)]
    reels_ranges[0][0]=0
    # if cum_frm_list = [22836, 51927, 76039, 106911] => reels_ranges = [ [0,22836] , [22837,51927] , [51928,76039] , [76040,106911] ]
    debug_print('reels_ranges = '+str(reels_ranges))
    
    # if there's just one reel it returns -1
    if reels_count==1:
        return (-1,reels_ranges)
    
    mid_time_frm = cum_frm_list[-1]/2
    for i in range(reels_count):
        if (cum_frm_list[i]<mid_time_frm) and (cum_frm_list[i+1]>=mid_time_frm):
            reel_idx = i+1
    
    '''
    reels_idx is the reel in which mid_time_frm falls.
    we want to move to the next reel if mid_time_frm falls in the 2nd half of the reels_idx-th reel!
    e.g the second example is an extreme case where mid_time_frm is in the 2nd half of the 2nd reel (reel_idx=1 but we return 2)
    '''
    
    mid_reel_frm = cum_frm_list[reel_idx-1] + 1 + (cum_frm_list[reel_idx]-cum_frm_list[reel_idx-1])/2
    debug_print('mid_time_frm = '+str(mid_time_frm))
    debug_print('reel_idx = '+str(reel_idx))
    debug_print('mid_reel_frm = '+str(mid_reel_frm))
    if mid_time_frm<mid_reel_frm:
        debug_print('returned reel_idx = '+str(reel_idx))
        return (reel_idx,reels_ranges)
    elif mid_time_frm>=mid_reel_frm:
        if reel_idx+1==reels_count:
            debug_print('returned reel_idx = '+str(reel_idx))
            return (reel_idx,reels_ranges)
        else:
            debug_print('returned reel_idx = '+str(reel_idx+1))
            return (reel_idx+1,reels_ranges)

# Custom Listbox with mouse over highlight effect
class CustomListBox(tk.Listbox):
    def __init__(self, master=None, *args, **kwargs):
        tk.Listbox.__init__(self, master, *args, **kwargs)

        self.bg = "white"
        self.fg = "black"
        self.highlight_bg = "yellow"
        self.highlight_fg = "blue"

        self.current = -1  # current highlighted item

        self.bind("<Motion>", self.on_motion)
        self.bind("<Leave>", self.on_leave)

    def reset_colors(self):
        """Resets the colors of the items"""
        for item in range(0, self.size()):
            self.itemconfig(item, {"bg": self.bg})
            self.itemconfig(item, {"fg": self.fg})

    def set_highlighted_item(self, index):
        """Set the item at index with the highlighted colors"""
        self.itemconfig(index, {"bg": self.highlight_bg})
        self.itemconfig(index, {"fg": self.highlight_fg})    

    def on_motion(self, event):
        """Calls everytime there's a motion of the mouse"""
        index = self.index("@%s,%s" % (event.x, event.y))
        if index == -1:
            return
        if self.current != -1 and self.current != index:
            self.reset_colors()
            self.set_highlighted_item(index)
        elif self.current == -1:
            self.set_highlighted_item(index)
        self.current = index

    def on_leave(self, event):
        self.reset_colors()
        self.current = -1

class Application(tk.Frame):
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.grid()
        self.createWidgets()
        self.current = -1

    def createWidgets(self):
        self.selectButton = tk.Button(self, text='Select XML file',command=self.selectXML,cursor="hand2")
        self.selectButton.grid(columnspan=1,column=0,row=0,sticky="nsew")

        self.searchButton = tk.Button(self, text='Search by name or UUID/CPL',command=self.searchXML,cursor="hand2")
        self.searchButton.grid(column=1,row=0,sticky="nsew")

        self.quitButton = tk.Button(self, text='Quit',command=quit,cursor="hand2")
        self.quitButton.grid(column=2,row=0,sticky="nsew")
        
        self.textbox = tk.Text(self, borderwidth=3, relief="sunken")
        self.textbox.config(font=("consolas", 10), undo=True, wrap='word',state=tk.DISABLED)
        self.textbox.grid(row=1, column=0,columnspan=3)

        self.canvas1 = tk.Canvas(self, width=CANVAS_WIDTH, height=CANVAS_HEIGHT)#, bg='white')
        self.canvas1.grid(row=2, column=0,columnspan=3,sticky="s")

        self.canvas2 = tk.Canvas(self, width=CANVAS_WIDTH*1.05, height=20)#, bg='white')
        self.canvas2.grid(row=3, column=0,columnspan=3,sticky="s")

    def selectXML(self):
        self.cleanTextbox()
        
        filetypes = [('XML file','*.xml')]
        file = tkFileDialog.askopenfile(parent=self, mode='rb', title='Choose a file', filetypes=filetypes, initialdir=DCP_FOLDER)
        if file != None:
            self.processXML(file.name)

    def searchXML(self):
        self.cleanTextbox()

        self.xml_files_list = recursive_glob_ignorecase(DCP_FOLDER)
        text_length = 160

        self.top = tk.Toplevel()
        self.top.title("DCP Interval Finder - Search")
        self.L = tk.Label(self.top, text="Insert part of name or UUID/CPL: ")
        self.L.grid(row=0,column=0)
        self.search_box = tk.Text(self.top, height=1, width=text_length-21)
        self.search_box.grid(row=0,column=1)
        self.autosubmit = tk.IntVar()
        self.autosubmit.set(AUTOSUBMIT)
        self.showftronly = tk.IntVar()
        self.showftronly.set(SHOW_FTR_ONLY)
        self.C = tk.Checkbutton(self.top, text="Auto", variable=self.autosubmit,cursor="hand2",command=lambda: self.update_listbox(None))
        self.C.grid(row=0,column=2)
        self.C2 = tk.Checkbutton(self.top, text="FTR", variable=self.showftronly,cursor="hand2",command=lambda: self.update_listbox(None))
        self.C2.grid(row=0,column=3)
        self.scrollbar = tk.Scrollbar(self.top)
        self.scrollbar.grid(row=1,column=4,sticky="nsw")
        self.Lb1 = CustomListBox(self.top,width=text_length,height=15,cursor="hand2")
        self.Lb1.bind("<<ListboxSelect>>", self.listbox_onclick)
        self.Lb1.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.Lb1.yview)

        filtered_xml_files_list = filter_by_pattern(self.xml_files_list,"",self.showftronly.get())
        for f in filtered_xml_files_list:
            self.Lb1.insert(tk.END, f)


        self.search_box.bind("<Key>", self.update_listbox)
        self.search_box.bind("<Return>", self.handle_ENTER)
        self.Lb1.grid(row=1,column=0,columnspan=4)
        self.search_box.focus_set()

    def highlight_pattern(self, txt, pattern, tag, start="1.0", end="end",regexp=False):
        '''Apply the given tag to all text that matches the given pattern

        If 'regexp' is set to True, pattern will be treated as a regular
        expression.
        '''

        start = txt.index(start)
        end = txt.index(end)
        txt.mark_set("matchStart", start)
        txt.mark_set("matchEnd", start)
        txt.mark_set("searchLimit", end)

        count = tk.IntVar()
        while True:
            index = txt.search(pattern, "matchEnd","searchLimit",
                                count=count, regexp=regexp)
            if index == "": break
            txt.mark_set("matchStart", index)
            txt.mark_set("matchEnd", "%s+%sc" % (index, count.get()))
            txt.tag_add(tag, "matchStart", "matchEnd")
        
    def addText(self,text):
        self.textbox.config(state=tk.NORMAL)
        self.textbox.insert(tk.INSERT,text)
        self.textbox.config(state=tk.DISABLED)

    def cleanTextbox(self):
        self.textbox.config(state=tk.NORMAL)
        self.textbox.delete(1.0, tk.END)
        self.textbox.config(state=tk.DISABLED)
        self.canvas1.delete("all")
        self.canvas2.delete("all")

    def processXML(self,file):
        if file==None:
            return

        xmldoc = minidom.parse(file)
        self.addText(file+"\n\n")
        itemlist = xmldoc.getElementsByTagName('MainPicture') 
        self.addText(str(len(itemlist))+" reel")
        if len(itemlist)>1:
            self.addText("s")
        self.addText(" found\n\n")
        cumulative_frames = 0
        cum_frm_list = []
        reel_ID = 1
        self.addText("Reel #\tReel's frames\t\tTime\n")
        for reel in itemlist:
            reel_frames = reel.getElementsByTagName("Duration")[0].childNodes[0].data
            cumulative_frames=cumulative_frames+int(reel_frames)
            self.addText(str(reel_ID)+"\t"+reel_frames+"\t\t"+frames_to_hms_string(cumulative_frames-int(reel_frames))+" -> "+frames_to_hms_string(cumulative_frames)+"\n")
            cum_frm_list.append(cumulative_frames)
            reel_ID = reel_ID+1
        
        self.addText('\nTotal frames:\t\t'+str(cumulative_frames)+"\n")
        self.addText('Total time:\t\t'+frames_to_hms_string(cumulative_frames)+"\n")
        
        mid_time = cumulative_frames/2
        self.addText('Mid time:\t\t'+frames_to_hms_string(mid_time)+"\n")
        (mid_reel,reels_ranges) = find_mid_reel(cum_frm_list)

        if mid_reel!=-1:
            self.addText('\nSuggested interval time:\t\t'+frames_to_hms_string(cum_frm_list[mid_reel-1] + FPS*TIME_OFFSET)+"\n")
            self.textbox.tag_configure("red", foreground = "red")
            self.highlight_pattern(self.textbox,"Mid time:", "red")
            self.textbox.tag_configure("green", foreground = "green")
            self.highlight_pattern(self.textbox,"Suggested interval time:", "green")
        else:
            self.addText('\nSuggested interval time:\t\t WARNING  This DCP has just 1 reel! Mid time is '+frames_to_hms_string(mid_time)+"\n")
            self.textbox.tag_configure("redbg", background = "red")
            self.highlight_pattern(self.textbox," WARNING ", "redbg")
            self.textbox.tag_configure("red", foreground = "red")
            self.highlight_pattern(self.textbox,"Suggested interval time:", "red")
        

        max_frm = reels_ranges[-1][-1]
        debug_print('max_frm = '+str(max_frm))
        def scaled(frm):
            if frm==0:
                return 1
            else:
                return frm*CANVAS_WIDTH/max_frm
        def color(idx):
            if idx==mid_reel:
                return "yellow"
            else:
                return "yellow"
        for idx,reel_x in enumerate(reels_ranges):
            debug_print('(idx,reel_x)')
            debug_print((idx,reel_x))
            debug_print('(scaled(reel_x[0]),scaled(reel_x[1]))')
            debug_print((scaled(reel_x[0]),scaled(reel_x[1])))
            self.canvas1.create_rectangle(scaled(reel_x[0]),CANVAS_HEIGHT/3,scaled(reel_x[1]),CANVAS_HEIGHT, fill=color(idx))
            if idx!=0 and idx!=len(reels_ranges):
                self.canvas2.create_text(scaled(reel_x[0]),0, text=frames_to_hms_string(cum_frm_list[idx-1]),anchor=tk.NW,font=("TkDefaultFont",6))
        self.canvas1.create_line(scaled(mid_time),0,scaled(mid_time),CANVAS_HEIGHT/3-1, fill="red", arrow=tk.LAST)
        self.canvas2.create_text(1,0, text="0:00:00",anchor=tk.NW,font=("TkDefaultFont",6))
        self.canvas2.create_text(CANVAS_WIDTH*1.05,0, text=frames_to_hms_string(cumulative_frames),anchor=tk.NE,font=("TkDefaultFont",6))
        if mid_reel!=-1:
            self.canvas1.create_line(scaled(cum_frm_list[mid_reel-1]),0,scaled(cum_frm_list[mid_reel-1]),CANVAS_HEIGHT/3-1, fill="green", arrow=tk.LAST)

    def handle_ENTER(self,event):
        word = str(self.search_box.get(1.0, tk.END))
        word = word [:-1] #remove newline
        filtered_xml_files_list = filter_by_pattern(self.xml_files_list,word,self.showftronly.get())
        if len(filtered_xml_files_list)==1:
            self.top.destroy()
            self.processXML(filtered_xml_files_list[0])
        return "break"

    def update_listbox(self,event):
        self.Lb1.delete(0, tk.END)

        word = str(self.search_box.get(1.0, tk.END))
        word = word [:-1] #remove newline

        if event!=None:
            if event.keycode==22:
                word = word [:-1] #remove last char
            else:
                word = word + str(event.char)

        filtered_xml_files_list = filter_by_pattern(self.xml_files_list,word,self.showftronly.get())
        for f in filtered_xml_files_list:
            self.Lb1.insert(tk.END, f)

        if len(filtered_xml_files_list)==0:
            if self.showftronly.get() == True:
                self.showftronly.set(0)
                self.update_listbox(None)
                return
            self.search_box.configure(bg='red')
        elif len(filtered_xml_files_list)==1:
            self.search_box.configure(bg='lime green')
            if self.autosubmit.get()==1:
                self.top.destroy()
                self.processXML(filtered_xml_files_list[0])
        else:
            self.search_box.configure(bg='white')

    def listbox_onclick(self, event):
        widget = event.widget
        selection=widget.curselection()
        if len(selection)>0:
            file_name = widget.get(selection[0])
            self.top.destroy()
            self.processXML(file_name)

app = Application()
app.master.title('DCP Interval Finder')
app.mainloop()
