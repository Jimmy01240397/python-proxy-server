import socket, sys, os, time
from _thread import *
import threading

listening_port = 8888
forwardaddr = ('192.168.10.254', 8888)
max_connection = 100
buffer_size = 8192

with open('locallist.conf', 'r') as f:
    locallist = f.readlines()
    f.close()

with open('forwardlist.conf', 'r') as f:
    forwardlist = f.readlines()
    f.close()

def start():    #Main Program
    global locallist
    global forwardlist
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('', listening_port))
        sock.listen(max_connection)
        print("[*] Server started successfully [ %d ]\n" %(listening_port))
    except Exception as e:
        print("[*] Unable to Initialize Socket")
        print(Exception)
        print(e)
        sys.exit(2)

    lasttime = time.time()
    while True:
        try:
            conn, addr = sock.accept() #Accept connection from client browser
            thread_max.acquire()
            start_new_thread(conn_string, (conn, addr)) #Starting a thread
            if time.time() - lasttime > 30:
                if os.path.isfile('reloadconf'):
                    with open('locallist.conf', 'r') as f:
                        locallist = f.readlines()
                        f.close()
                    with open('forwardlist.conf', 'r') as f:
                        forwardlist = f.readlines()
                        f.close()
                    os.remove('reloadconf')
                else:
                    with open('locallist.conf', 'w') as f:
                        locallist = list(set(locallist))
                        f.writelines(locallist)
                        f.close()
                    with open('forwardlist.conf', 'w') as f:
                        forwardlist = list(set(forwardlist))
                        f.writelines(forwardlist)
                        f.close()
                lasttime = time.time()

        except KeyboardInterrupt:
            closesocket([sock])
            print("\n[*] Graceful Shutdown")
            sys.exit(1)

def conn_string(conn, addr):
    try:    
        data = conn.recv(buffer_size) #Recieve client data
        #print(data)

        first_line = data.decode().split('\n')[0]

        firstdata = first_line.split()

        typedata = firstdata[0]

        url = firstdata[1]

        httpver = firstdata[2]

        http_pos = url.find("://") #Finding the position of ://
        if(http_pos==-1):
            temp=url
        else:
            temp = url[(http_pos+3):]
        
        port_pos = temp.find(":")

        webserver_pos = temp.find("/")
        if webserver_pos == -1:
            webserver_pos = len(temp)
        webserver = ""
        port = -1
        if(port_pos == -1 or webserver_pos < port_pos):
            port = 80
            webserver = temp[:webserver_pos]
        else:
            port = int((temp[(port_pos+1):])[:webserver_pos-port_pos-1])
            webserver = temp[:port_pos]

        if typedata == 'CONNECT':
            conn.send((httpver + ' 200 OK\r\n\r\n').encode())
            data = conn.recv(buffer_size) #Recieve client data
        
        weburl = webserver + ':' + str(port) + '\n'

        remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        if weburl in locallist:
            try:
                remote.connect((webserver, port))
            except socket.error:
                remote.connect(forwardaddr)
                do_forward(remote, weburl, httpver)
        elif weburl in forwardlist:
            remote.connect(forwardaddr)
            do_forward(remote, weburl, httpver)
        else:
            try:
                remote.connect((webserver, port))
            except socket.error:
                remote.connect(forwardaddr)
                do_forward(remote, weburl, httpver)
                forwardlist.append(weburl)

        #print(remote.error)
        
        remote.send(data)
        
        if weburl not in locallist and weburl not in forwardlist:
            proxy_ontest(conn, remote, addr, (webserver, port), httpver)
        thread_max.acquire()
        start_new_thread(proxy_server, (conn, remote, addr, (webserver, port))) #Starting a thread
        thread_max.acquire()
        start_new_thread(proxy_server, (remote, conn, (webserver, port), addr)) #Starting a thread
    except KeyboardInterrupt:
        closesocket([conn])
    except Exception as e:
        closesocket([conn])
        print('connect error:')
        print(e)
    finally:
        thread_max.release()
        #print("end")
        #pass

def do_forward(sock, weburl, httpver):
    sock.send(('CONNECT ' + weburl.strip() + ' ' + httpver + '\r\n\r\n').encode())
    sock.recv(buffer_size)

def proxy_ontest(conn, remote, addr, remoteaddr, httpver):
    weburl = str(remoteaddr[0]) + ':' + str(remoteaddr[1]) + '\n'
    try:
        remote.settimeout(10)
        reply = remote.recv(buffer_size)
        if(len(reply)>0):
            conn.send(reply)
            locallist.append(weburl)
        
    except socket.timeout:
        closesocket([remote])
        remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote.connect(forwardaddr)
        do_forward(remote, weburl, httpver)
        forwardlist.append(weburl)
    except KeyboardInterrupt:
        closesocket([remote, conn])
    except Exception:
        closesocket([remote, conn])

def proxy_server(conn, remote, addr, remoteaddr):
    try:
        remote.settimeout(10)
        while 1:
            reply = remote.recv(buffer_size)

            if(len(reply)>0):
                conn.send(reply)
            else:
                break

        closesocket([remote, conn])

    except KeyboardInterrupt:
        closesocket([remote, conn])
    except Exception:
        closesocket([remote, conn])
    finally:
        thread_max.release()
        #print("end")
        #pass

def closesocket(conn):
    for sock in conn:
        try:
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
        except Exception:
            pass


if __name__ == "__main__":
    thread_max = threading.BoundedSemaphore(1000)
    start()
