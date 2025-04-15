# Version: 3.0
import socket; # Netzwerkfunktionen
import threading; # Threadfunktionen (Asynchrones Skript; mehrere können gleichzeitig ausgeführt werden)
import json; # Kodierung von strings, integers
import pickle; # Kodierung von komplexen Objekten und Datentypen
import sys; # System zum Löschen von Zeilen in der Konsole

onClientJoin = onConnect = onDisconnect = lambda this: None

class Message(): # Nachrichten-Klasse bestehend aus Absender, Typ und Inhalt
    def __init__(self, sender, type, content):
            self.sender = sender; # bspw. Server, Client1, etc.
            self.type = type; # Art der Nachricht z.B. Textnachricht oder Funktion die ausgeführt werden soll 
            self.content = content; # Inhalt z.B. die Textnachricht als String oder Argumente für die auszuführende Funktion
    
    def __str__(self): # Ausgabe wenn Objekt der Klasse in Print-Befehl verwendet wird
        return f"Message from '{self.sender}': ({self.type})\n {self.content}";
    
class Server(): # Server-Klasse
    class Client(): # Speichert relevante Daten zu einem der Clients auf Seiten des Servers
        def __init__(self, parent, conn, addr):
            
            self.parent = parent; # verwendet um auf Server-Methoden zuzugreifen
            self.conn = conn; # verwendet um Client anzusprechen
            self.addr = addr; # IP-Adresse des Clients
            if self.parent.unusedNames != []: # Versucht erst disconnectete Clients zu ersetzen
                self.name = self.parent.unusedNames[0];
                self.parent.unusedNames.pop(0);
            else: # alternativ neuen Client-Namen erstellen
                self.name = str(len(self.parent.clients)+1);
            client_thread = threading.Thread(target=self.handleClient, args=(conn, addr));
            client_thread.start(); #Started Thread(läuft im Hintergrund unabhängig zu Main-Code)
            self.parent.threads.append(client_thread);
        
        def handleClient(self, conn, addr): # Skript welches einen spezifisches Client verwaltet
            print(f"Connected with {addr}");
            onConnect(self)
            message = Message("server", "setName", self.name); # Befehl an Client um Namen zu setzen
            self.parent.send(conn, message); # §
            onClientJoin()
            while self.parent.on:
                try:
                    message = self.parent.receive(conn, addr); # Nachrichten werden angenommen
                    if message.type in self.parent.messageFunctions: # Abgleich von Typ mit möglichen Funktionen
                        self.parent.messageFunctions[message.type](message.sender, message.content); # Ausführung der jeweiligen Funktion
                    else: # Alternativ Ausgabe der Nachricht in Konsole
                        print(message); 
                except Exception as e: # Bei Verbindungsabbruch Schleife beenden
                    print(e);
                    break;
            conn.close(); # Verbindung beenden
            self.parent.unusedNames.append(self.name); # Namen zu Liste von verfügbaren Namen hinzufügen
            print(f"Disconnected {addr}");
            onDisconnect(self)
            self.parent.clients.remove(self); # Client-Objekt auf Server-Seite löschen
            
    def __init__(self, host, port, dataSize, encoding = "json", maxConnections = 4, console = False):
        self.threads = []
        self.on = True
        self.clients = []; # Liste an verbundenen Clients
        self.host = host;
        self.port = port;
        self.dataSize = dataSize; # maximale Größe von Nachrichten
        self.encoding = encoding; # Kodierung in "json"(simple Datentypen) oder "pickle"(vielseitiger, Übermittlung von bspw. Klassen)
        self.messageFunctions = {"userMessage": self.userMessage}; # Liste an verwendbaren Funktionen beim Empfangen von Nachrichten
        self.unusedNames = []; # Neuzuvergebende Client-Namen
        self.maxConnections = maxConnections; # Maximale Anzahl an Clients
        self.console = console; # Verwendung von Nachrichtenaustausch durch Konsoleninputs (True/False)
        self.start_server();
        
    def start_server(self): # Starten des Servers
        
        print("Starting server...");
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
        self.server_socket.bind((self.host, self.port)); # Festlegung von IP und Port
        self.server_socket.listen(self.maxConnections); # Start
        print(f"Listening on {self.host}:{self.port}");
        if self.console:
            consoleThread = threading.Thread(target=self.consoleLoop);
            consoleThread.start(); # Starten des Konsolen-Threads
            self.threads.append(consoleThread);
        
        connectThread = threading.Thread(target=self.connectLoop);
        connectThread.start(); # Starten des Verbindungs-Threads
        self.threads.append(connectThread);
    
    def close(self):
        self.on = False
        for thread in self.threads:
            thread.join()
            self.threads.remove(thread)
        for client in self.clients:
            client.conn.close()
            self.clients.remove(client)
        self.server_socket.close()
        print("Server closed")
       
    def connectLoop(self):    
        while self.on:
            if len(self.clients) < self.maxConnections: # Verbindungsaufbau zu Clients solange Maximum nicht erreicht
                self.connect();

    def consoleLoop(self):
        print("Console activated");
        while self.on:
            content = input("");
            self.sendAll(Message("server", "userMessage", content)); # Inputversendung an alle Clients
            print(f"server: {content}");
            
    def connect(self): # Verbindungsversuch mit neuem Client
        self.server_socket.settimeout(1)
        try:
            conn, addr = self.server_socket.accept()
            self.clients.append(self.Client(self, conn, addr));
        except TimeoutError as e:
            return e
    
    def receive(self, conn, addr): # Annahme von Nachrichten
        data = conn.recv(self.dataSize)
        if not data: # Fehler bei Verbindungstrennung
            raise Exception("disconnected", addr)
        message = decode(data, self.encoding);
        return message;
    
    def sendAll(self, message): # Senden einer Nachricht an alle Clients
        for client in self.clients:
            self.send(client.conn, message);
    
    def send(self, conn, message): # Senden einer Nachricht an spezifischen Client
        conn.sendall(encode(message, self.encoding));
    
    def userMessage(self, sender, content): # Ausgabe von empfangener Nachricht
        print(f"{sender}: {content}");
        self.sendAll(Message(sender, "userMessage", content));
    
class Client(): # Client-Klasse
    def __init__(self, host, port, dataSize, encoding = "json", console = False, debug = 1):
        self.on = True
        self.threads = []
        self.host = host;
        self.port = port;
        self.dataSize = dataSize; # maximale Größe von Nachrichten
        self.encoding = encoding; # Kodierung in "json"(simple Datentypen) oder "pickle"(vielseitiger, Übermittlung von bspw. Klassen)
        self.console = console; # Verwendung von Nachrichtenaustausch durch Konsoleninputs (True/False)
        self.name = "unknown client"; # Temporärer Name vor Vergabe durch Server
        self.debug = debug;
        self.messageFunctions = {"userMessage": self.userMessage, 
                                 "setName": self.setName}; # Liste an verwendbaren Funktionen beim Empfangen von Nachrichten
        self.connect(host, port); 
        
    def connect(self, host, port): # Verbindung zu Server
        
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((host, port));
        if self.debug > 0:
            print(f"Connected to host: {self.host}: port {self.port}");
        recv_thread = threading.Thread(target=self.receive_messages, args=(self.client_socket,))
        recv_thread.start(); # Starten des Client-Threads
        self.threads.append(recv_thread);
        if self.console:
            consoleThread = threading.Thread(target=self.consoleLoop);
            consoleThread.start(); # Starten des Konsolen-Threads
            self.threads.append(consoleThread);    
    def close(self):
        self.on = False;
        for thread in self.threads:
            thread.join()
            self.threads.remove(thread)
        self.client_socket.shutdown(socket.SHUT_RDWR)
        self.client_socket.close();
        print("Disconnected");
        
    
    def consoleLoop(self):
        if self.debug > 0:
            print("Console activated");
        while self.on:
            self.send(Message(self.name, "userMessage", input(""))); # Versenden von Input-Nachrichten an Server
            
    def receive_messages(self, sock): # Verfahren mit empfangenen Nachrichten
        if self.debug > 0:
            print("Now receiving messages");
        while self.on:
            try:
                self.client_socket.settimeout(1)
                try:
                    message = self.receive();
                    if message.type in self.messageFunctions: # Abgleich von Typ mit möglichen Funktionen
                        self.messageFunctions[message.type](message.sender, message.content); # Ausführung der jeweiligen Funktion
                    else: # Alternativ Ausgabe der Nachricht in Konsole
                        print(message); 
                    if self.debug > 1:
                        print(f"Executed {message.type} from {message.sender}");
                except TimeoutError as e:
                    pass
            except Exception as e:
                if self.debug > 1:
                    print(e);
                break;
    
    def receive(self): # Annahme von Nachrichten
        data = self.client_socket.recv(self.dataSize);
        if not data:
            raise Exception("disconnected")
        message = decode(data, self.encoding);
        if self.debug > 1:
            print(message);
        return message;

    def send(self, message): # Versand von Nachrichten
        self.client_socket.sendall(encode(message, self.encoding));
    
    def userMessage(self, sender, content): # Ausgabe von Nachrichten
        print(f"{sender}: {content}");
    
    def setName(self, sender, name): # Namensvergabe durch Server
        self.name = name;
    
def encode(message, type): # Kodierung von Nachrichten
    if type == "json":
        encoded = {
            'sender': message.sender,
            'type': message.type,
            'content': message.content
        }

        encoded = json.dumps(encoded);
        encoded = encoded.encode('utf-8');
        return encoded;
        
    elif type == "pickle":
        encoded = pickle.dumps(message);
        return encoded;
          
def decode(encoded, type): # Dekodierung von Nachrichten
    if type == "json":
        message = json.loads(encoded.decode('utf-8'));
        return Message(message['sender'], message['type'], message['content']);
    
    elif type == "pickle":
        message = pickle.loads(encoded);
        return message;


if __name__ == '__main__': # Nur bei direktem Ausführen des Skripts verwendet
    server = Server('localhost', 54321, 1024, "pickle", 4, True); # Starten eines Test-Servers
