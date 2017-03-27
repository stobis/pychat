import socket
import sys
import threading
import queue
from protocol import *

# Init vars
debug = True
#HOST = ''
lock = threading.RLock()


# Glowny serwer
class EchoServer:
    def __init__(self, host, port):
        self.clients = []   # informacje o klientach
        self.open_socket(host, port)
    
    
    def open_socket(self, host, port):
        """ 
        Metoda tworząca server, na hoscie: host i porcie: port
        """
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind( (host, port) ) 
        self.server.listen(5)


    def run(self):
        
        while True:     
            # Akceptuje podlaczenie sie klienta       
            clientSocket, clientAddr = self.server.accept()
            
            request = clientSocket.recv(BUFSIZE)
            request = request.decode("UTF-8")
            request = request.split(SEPARATOR)
            
            if debug:
                print("SERVER LOG: Zgłoszenie klienta, adres: {0} {1}".format(clientAddr, request))
            
            
            # Sprawdza czy prosba ma wlasciwy format i czy nazwa uzytkownika jest wolna
            if (len(request) != 4 or request[1] != REGISTER_USER or request[2] == "ALL"):
                clientSocket.send(bytes(STATUS_FAIL, "UTF-8"))
                continue
                
            request_username = request[2]
            is_username_free = True
            
            lock.acquire()
            for x in self.clients:
                if (x[1] == request_username):
                    is_username_free = False
            lock.release()
           
            if (is_username_free is False):
                clientSocket.send(bytes(STATUS_FAIL, "UTF-8"))
                continue
            
            # jesli sprawdzanie sie powiodlo, wysyla potwierdzenie klientowi
            clientSocket.send(bytes(STATUS_OK, "UTF-8"))
            
            """
            Tworze 2 watki - jeden bedzie odbieral wiadomosci od klienta,
            do drugiego wszyscy sie beda mogli podlaczyc, bedzie on pisal do klienta
            """
            socket_writer = ClientWriter(clientSocket, self)
            asd = Client(clientSocket, clientAddr, self, socket_writer)
            
            # Dodaje skonfigurowane polaczenie z klientem do listy wszystkich uzytkownikow
            lock.acquire()
            self.clients.append((clientSocket, request_username, asd, socket_writer))
            lock.release()
            if debug:
                self.number_of_clients()

            # Uruchamiam watki polaczenia z klientem
            socket_writer.start()
            asd.start()
            
            
            # Rozsylam wiadomosc o nowym uzytkowniku do wszystkich
            lock.acquire()
            echodane = SEPARATOR + SHOW_USER + SEPARATOR + request_username + SEPARATOR
            err = []
            
            for (client_socket, client_username, client_manager, client_writer) in self.clients:
                try:
                    client_writer.toSend.put(echodane)   # kazdy wysyla sobie                          
                    if (client_username != request_username): #jesli nie jestem soba to sobie pozostalych wysylam
                        socket_writer.toSend.put(SEPARATOR + SHOW_USER + SEPARATOR + client_username + SEPARATOR)
                except:
                    err.append(client_socket)                        
            self.clean_clients(err)    
            lock.release()
                    
    
    def number_of_clients(self):
        print("Liczba klientów: {0}".format(len(self.clients)))
    
    def clean_client(self, client):
        # must be changed!!!!
        delname = ""
        for i in range(len(self.clients)):
           
            if (self.clients[i][0] == client):
                try:
                    
                    delname = self.clients[i][1]
                    
                    self.clients[i][2].running = False
                    self.clients[i][3].running = False
                    
                    self.clients.remove(self.clients[i])
                    client.close()
                    
                    if debug:
                        self.number_of_clients()
                    
                    break
                except Exception as e:
                    if debug:
                        print("Exception: usuwanie klienta", type(e))
                    return
        if (delname == ""):
            return 
        # Rozsylam wiadomosc o usunieciu uzytkownika do wszystkich
        echodane = SEPARATOR + HIDE_USER + SEPARATOR + delname + SEPARATOR
        err = []
        
        for (client_socket, client_username, client_manager, client_writer) in self.clients:
            try:
                client_writer.toSend.put(echodane)   # kazdy wysyla sobie                          
            except:
               err.append(client_socket)                        
        self.clean_clients(err)             
    
    def clean_clients(self, err):
        for client in err:
            self.clean_client(client)
            
            
            
# Watek odbierajacy wiadomosci od klienta
class Client(threading.Thread):

    def __init__(self, clientSocket, clientAddr, server, clientWriter):
        threading.Thread.__init__(self)
        self.clientSocket = clientSocket;
        self.clientAddr = clientAddr;
        self.server = server
        self.clientWriter = clientWriter
        self.running = False
        
    def run(self):
    
        self.running = True
        while self.running:
            data = b''
            try:
                data = self.clientSocket.recv(BUFSIZE);
                if debug:
                    print("[DATA]{0}[/DATA]".format(data))
                
                if data:                                
                    echodane = data.decode('UTF-8')
                    echodaneSplitted = echodane.split(SEPARATOR)
                    
                    # Sprawdzanie rodzaju komunikacji
                    if (echodaneSplitted[1] == PING):
                        try:
                            self.clientWriter.toSend.put(echodane)                            
                        except:
                            lock.acquire()
                            self.server.clean_client(self.clientWriter)                        
                            lock.release()
                        continue
                    
                    if (echodaneSplitted[1] != SEND_MSG):
                        print("JAKAS NIEDOZWOLONA KOMENDA!!!")
                        continue
                    
                    # Gdy chodzi o wyslanie wiadomosci miedzy uzytkownikami
                    err = []
                    lock.acquire()
                    for (client_socket, client_username, client_manager, client_writer) in self.server.clients:
                        if ((client_username == echodaneSplitted[3] or client_username == echodaneSplitted[2] or echodaneSplitted[3] == "ALL") is not True):
                            continue
                        try:
                            client_writer.toSend.put(echodane)                            
                        except:
                            err.append(client_socket)
                        
                    self.server.clean_clients(err)    
                    lock.release()
                else:
                    self.running = False
                    lock.acquire()
                    self.server.clean_client(self.clientSocket)
                    lock.release()
                    if debug:
                        print("IF C clause: {0}".format(data))
                    break
                    
            except Exception as e:
                lock.acquire()
                self.server.clean_client(self.clientSocket)
                lock.release()
                self.running = False
                if debug:
                    print("EXCEPT clasue: {0}, exception: {1}".format(data, type(e)))
                break

# Watek obslugujacy wysylanie wiadomosci do klienta
class ClientWriter(threading.Thread):

    def __init__(self, clientSocket, server):
        threading.Thread.__init__(self)
        self.clientSocket = clientSocket;
        self.server = server
        self.toSend = queue.Queue()
        self.running = False
        
    def run(self):
        self.running = True
        while self.running:
            data = b''
            try:
                data = self.toSend.get()    # kolejka jest thread-safe
                if debug:
                    print("[DATA Q]{0}[/DATA Q]".format(data))
                
                if data:                                
                    # Wysylanie kolejnej wiadomosci poprzez socket klienta
                    try:
                        self.clientSocket.send(bytes(data, 'UTF-8'))          
                    except:
                        lock.acquire()
                        self.server.clean_client(self.clientSocket)
                        lock.release()
                else:
                    self.running = False
                    lock.acquire()
                    self.server.clean_client(self.clientSocket)
                    lock.release()
                    if debug:
                        print("IF CW clause: {0}".format(data))
                    break
                    
            except Exception as e:
                lock.acquire()
                self.server.clean_client(self.clientSocket)
                lock.release()
                self.running = False
                if debug:
                    print("EXCEPT CW clause: {0}, exception: {1}".format(data), type(e))
                break

# Stworzenie i uruchomienie serwera
server = EchoServer(HOST, PORT)
server.run()

        
