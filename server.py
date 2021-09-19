import socket, sys, os, time
from _thread import *

try:
    listening_port = 8888
    forwardaddr = ('192.168.10.254', 8888)
except KeyboardInterrupt:
    print("\n[*] User has requested an interrupt")
    print("[*] Application Exiting.....")
    sys.exit()

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
            start_new_thread(conn_string, (conn, addr)) #Starting a thread
            if time.time() - lasttime > 30:
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
            try:
                sock.shutdown(socket.SHUT_RDWR)
                sock.close()
            except Exception:
                pass
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

        start_new_thread(proxy_server, (conn, remote, addr, (webserver, port))) #Starting a thread
        start_new_thread(proxy_server, (remote, conn, (webserver, port), addr)) #Starting a thread
    except KeyboardInterrupt:
        try:
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()
        except Exception:
            pass
    except Exception as e:
        try:
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()
        except Exception:
            pass
        print('connect error:')
        print(e)

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
            dar = float(len(reply))
            dar = float(dar/1024)
            dar = "%.3s" % (str(dar))
            dar = "%s KB" % (dar)
#            print("[*] Request Done: %s => %s : %s <=" % (str(remoteaddr[0]), str(addr[0]), str(dar)))
            locallist.append(weburl)
        
    except socket.timeout:
        try:
            remote.shutdown(socket.SHUT_RDWR)
            remote.close()
        except Exception:
            pass
        remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote.connect(forwardaddr)
        do_forward(remote, weburl, httpver)
        forwardlist.append(weburl)
    except KeyboardInterrupt:
        try:
            remote.shutdown(socket.SHUT_RDWR)
            remote.close()
        except Exception:
            pass
        try:
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()
        except Exception:
            pass
    except Exception as e:
        try:
            remote.shutdown(socket.SHUT_RDWR)
            remote.close()
        except Exception:
            pass
        try:
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()
        except Exception:
            pass

def proxy_server(conn, remote, addr, remoteaddr):
    try:
        while 1:
            reply = remote.recv(buffer_size)

            if(len(reply)>0):
                conn.send(reply)
                
                dar = float(len(reply))
                dar = float(dar/1024)
                dar = "%.3s" % (str(dar))
                dar = "%s KB" % (dar)
#                print("[*] Request Done: %s => %s : %s <=" % (str(remoteaddr[0]), str(addr[0]), str(dar)))

            else:
                break

        try:
            remote.shutdown(socket.SHUT_RDWR)
            remote.close()
        except Exception:
            pass
        try:
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()
        except Exception:
            pass
#        print("[*] Socket Close: %s => %s" % (str(remoteaddr[0]), str(addr[0])))


    except KeyboardInterrupt:
        try:
            remote.shutdown(socket.SHUT_RDWR)
            remote.close()
        except Exception:
            pass
        try:
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()
        except Exception:
            pass
    except Exception as e:
        try:
            remote.shutdown(socket.SHUT_RDWR)
            remote.close()
        except Exception:
            pass
        try:
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()
        except Exception:
            pass

start()
