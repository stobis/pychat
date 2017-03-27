from socket import *
from protocol import *

import time
import sys
import threading
import queue

import tkinter as tk

# init variables
debug = True

username = sys.argv[1]
print(username)

# init connection with server
s = socket(AF_INET, SOCK_STREAM) # creat socket
s.connect((HOST, PORT)) # make connection

register_request = SEPARATOR + REGISTER_USER + SEPARATOR + username + SEPARATOR
s.send(bytes(register_request, 'UTF-8'))

status = s.recv(BUFSIZE)
status = status.decode("UTF-8")
print(status)

if (status == STATUS_FAIL):
    print("SERWER ODMOWIL REJESTRACJI!\nPrawdopodobnie uzyta nazwa uzytkownika jest juz zajeta lub zastrzezona. Sprobuj ponownie.\n")
    s.close()
    exit()

# cause im registered, now i can make a threads for program

class MsgRecv(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.messages = queue.Queue()
        self.running = False
        
    def run(self):
        
        self.running = True
        
        while self.running:
            try:
                dane = s.recv(BUFSIZE)
                
                echodane = dane.decode('UTF-8')
                echodane = echodane.split(SEPARATOR+SEPARATOR)
                
                if debug:
                    print(echodane)
                
                #Gdyby przyszly sklejone
                for i in range(len(echodane)-1):
                    echodane[i] += SEPARATOR
                
                for i in range(len(echodane)-1):
                    echodane[len(echodane)-i-1] = SEPARATOR + echodane[len(echodane)-i-1]
                    
                for x in echodane:
                    self.messages.put(x)
                
                time.sleep(1)
                if debug:
                    print("CLIENT RECEIVED {0}".format(echodane))            
                
            except Exception as e:
                
                if debug:
                    print(type(e))
                self.running = False
                self.messages = []
                s.close()
                exit()
        print("ASD\n")
        s.close()
        

listener = MsgRecv()
listener.start()

# GUI

class MyApp:
    def __init__(self, root, listener):
        self.listener = listener
        
        self.root = root
        self.root.title("Chat: " + username)
        self.root.minsize(600,400)
        
        self.mainFrame = tk.Frame(self.root)
        self.mainFrame.grid(row=0, column=0, sticky=tk.N + tk.S + tk.W + tk.E)
        self.mainFrame.myName = "MainFrame"
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        
        self.frame00 = tk.Text(self.mainFrame, bg="white")
        self.frame00.grid(column=0, row=0, sticky=tk.N + tk.S + tk.W + tk.E)
        self.frame00.myName = "Frame00"
        self.frame00.config(state="disabled")

        self.frame01 = tk.Listbox(self.mainFrame, bg="white")
        self.frame01.grid(column=1, row=0, rowspan=2, sticky=tk.N + tk.S + tk.W + tk.E)
        self.frame01.myName = "Frame01"

        self.frame01.insert('end', "ALL")
        self.frame01.selection_set(0)


        self.frame10 = tk.Text(self.mainFrame, bg="white")
        self.frame10.grid(column=0, row=1, sticky=tk.N + tk.S + tk.W + tk.E)
        self.frame10.myName = "Frame10"
        
        self.frame20 = tk.Frame(self.mainFrame, bg="white")
        self.frame20.grid(column=0, row=2, sticky=tk.N + tk.S + tk.W + tk.E)
        self.frame20.myName = "Frame20"
        
        self.frame21 = tk.Frame(self.mainFrame, bg="white")
        self.frame21.grid(column=1, row=2, sticky=tk.N + tk.S + tk.W + tk.E)
        self.frame21.myName = "Frame21"
        
        
        self.mainFrame.rowconfigure(0,weight=4)
        self.mainFrame.rowconfigure(1,weight=2)
        self.mainFrame.rowconfigure(2,weight=1)
        
        self.mainFrame.columnconfigure(0,weight=3)
        self.mainFrame.columnconfigure(1,weight=1)
        
        self.ok_button = tk.Button(self.frame20, text="Send Message", command=self.sendMessageHandler)
        self.ok_button.pack(fill='both')
        self.ok_button.myName="OK Button"
        self.ok_button.focus_force()

        self.no_button = tk.Button(self.frame21, text="Exit", command=self.buttonExitClick)
        self.no_button.myName = "No Button"
        self.no_button.pack(fill='both')
        
        
        #bindowanie na poziomie aplikacji
        self.root.bind_all("<Return>", self.sendMessageHandlerRet)
        self.receiveMessage()
        
    def addUser(self, username):
        self.frame01.insert('end', username)
        return
        
    def removeUser(self, username):
        userlist = self.frame01.get(0, 'end')
        it = 0
        for x in userlist:
            print(x)
            if(x == username):
                self.frame01.delete(it)
                return
            it+=1
        return
    
    def addNewMessageInfo(self, text):
        self.frame00.config(state="normal")
        self.frame00.insert('end', text)
        self.frame00.config(state="disabled")
        return
    
    def sendMessageHandlerRet(self, args):
        self.sendMessageHandler()
        return
        
    def sendMessageHandler(self):
        if debug:
            print("In messagehangler\n")
            
        cur = self.frame01.curselection()
        if (len(cur) is 0):
            self.addNewMessageInfo("Musisz wybrać użytkownika!\n")
            return
        
        to = self.frame01.get(cur)
        msg = self.frame10.get("1.0", "end-1c")
        
        if(msg == "" or msg == "\n"):
            self.addNewMessageInfo("Musisz podać wiadomość!\n")
            return
        
        MESSAGE = SEPARATOR + SEND_MSG + SEPARATOR + username + SEPARATOR + to + SEPARATOR + str(len(msg)) + SEPARATOR + msg + "\n" + SEPARATOR
        
        if debug:
            print("Wiadomość: {0}".format(MESSAGE))
        
        self.frame10.delete("1.0", "end")
        
        s.send(bytes(MESSAGE, 'UTF-8'))
        return

    def receiveMessage(self):
        if debug:
            print("In receive\n")
        if (self.listener.messages.empty() is not True):
            echodane = self.listener.messages.get()
            echodane = echodane.split(SEPARATOR)
            
            if debug:
                print(echodane)
              
            if (echodane[1] == PING):
                pass  
            elif (echodane[1] == SEND_MSG):
                self.addNewMessageInfo("{0} => {1}: {2}".format(echodane[2], echodane[3], echodane[5]))
            elif (echodane[1] == SHOW_USER):
                self.addUser(echodane[2])
            elif (echodane[1] == HIDE_USER):
                self.removeUser(echodane[2])
            else:
                print("A TEJ KOMENDY NIE ZNAM!!!")
                
        self.root.after(100, self.receiveMessage)
        
    def buttonExitClick(self):
        self.listener.running = False
        print("THEEND")
        self.root.destroy()

root = tk.Tk()
myapp = MyApp(root, listener)
root.mainloop()
exit()
