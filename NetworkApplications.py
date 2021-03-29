#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import argparse
import socket
import os
import sys
import struct
import time
import select
import random


def setupArgumentParser() -> argparse.Namespace:
        parser = argparse.ArgumentParser(
            description='A collection of Network Applications developed for SCC.203.')
        parser.set_defaults(func=ICMPPing, hostname='lancaster.ac.uk')
        subparsers = parser.add_subparsers(help='sub-command help')
        
        parser_p = subparsers.add_parser('ping', aliases=['p'], help='run ping')
        parser_p.set_defaults(timeout=4)
        parser_p.add_argument('hostname', type=str, help='host to ping towards')
        parser_p.add_argument('--count', '-c', nargs='?', type=int,
                              help='number of times to ping the host before stopping')
        parser_p.add_argument('--timeout', '-t', nargs='?',
                              type=int,
                              help='maximum timeout before considering request lost')
        parser_p.set_defaults(func=ICMPPing)

        parser_t = subparsers.add_parser('traceroute', aliases=['t'],
                                         help='run traceroute')
        parser_t.set_defaults(timeout=4, protocol='icmp')
        parser_t.add_argument('hostname', type=str, help='host to traceroute towards')
        parser_t.add_argument('--timeout', '-t', nargs='?', type=int,
                              help='maximum timeout before considering request lost')
        parser_t.add_argument('--protocol', '-p', nargs='?', type=str,
                              help='protocol to send request with (UDP/ICMP)')
        parser_t.set_defaults(func=Traceroute)

        parser_w = subparsers.add_parser('web', aliases=['w'], help='run web server')
        parser_w.set_defaults(port=8080)
        parser_w.add_argument('--port', '-p', type=int, nargs='?',
                              help='port number to start web server listening on')
        parser_w.set_defaults(func=WebServer)

        parser_x = subparsers.add_parser('proxy', aliases=['x'], help='run proxy')
        parser_x.set_defaults(port=8000)
        parser_x.add_argument('--port', '-p', type=int, nargs='?',
                              help='port number to start web server listening on')
        parser_x.set_defaults(func=Proxy)
        args = parser.parse_args()
        return args


class NetworkApplication:

    def checksum(self, dataToChecksum: str) -> str:
        csum = 0
        countTo = (len(dataToChecksum) // 2) * 2
        count = 0

        while count < countTo:
            thisVal = dataToChecksum[count+1] * 256 + dataToChecksum[count]
            csum = csum + thisVal
            csum = csum & 0xffffffff
            count = count + 2

        if countTo < len(dataToChecksum):
            csum = csum + dataToChecksum[len(dataToChecksum) - 1]
            csum = csum & 0xffffffff

        csum = (csum >> 16) + (csum & 0xffff)
        csum = csum + (csum >> 16)
        answer = ~csum
        answer = answer & 0xffff
        answer = answer >> 8 | (answer << 8 & 0xff00)

        answer = socket.htons(answer)

        return answer

    def printOneResult(self, destinationAddress: str, packetLength: int, time: float, ttl: int, destinationHostname=''):
        if destinationHostname:
            print("%d bytes from %s (%s): ttl=%d time=%.2f ms" % (packetLength, destinationHostname, destinationAddress, ttl, time))
        else:
            print("%d bytes from %s: ttl=%d time=%.2f ms" % (packetLength, destinationAddress, ttl, time))

    def printAdditionalDetails(self, packetLoss=0.0, minimumDelay=0.0, averageDelay=0.0, maximumDelay=0.0):
        print("%.2f%% packet loss" % (packetLoss))
        if minimumDelay > 0 and averageDelay > 0 and maximumDelay > 0:
            print("rtt min/avg/max = %.2f/%.2f/%.2f ms" % (minimumDelay, averageDelay, maximumDelay))


class ICMPPing(NetworkApplication):

    packetLength = 0

    def receiveOnePing(self, icmpSocket, destinationAddress, ID, timeout):
        # 1. Wait for the socket to receive a reply
        while True:
            ready = select.select([icmpSocket],[], [], timeout)
            if ready[0] == []:
                print("not ready")
                return
            packet, address = icmpSocket.recvfrom(1024)
            print(packet)
            print(address)
            self.packetLength = len(packet)
            icmpHeader = packet[20:28]
            type, code, checksum, packetID, sequence = struct.unpack('bbHHh', icmpHeader)
            print("type:")
            print(type)
            print("code")
            print(code)
            print("checksum:")
            print(checksum)
            print("id:")
            print(id)
            print("sequence")
            print(sequence)
            break
        # 2. Once received, record time of receipt, otherwise, handle a timeout
        if(packetID == ID):
            print("id is the same")
        else:
            print("its fucked lmao")
        # 3. Compare the time of receipt to time of sending, producing the total network delay
        # 4. Unpack the packet header for useful information, including the ID
        # 5. Check that the ID matches between the request and reply
        # 6. Return total network delay
        return time.time()

    def sendOnePing(self, icmpSocket, destinationAddress, ID):
        # 1. Build ICMP header
        header = struct.pack('bbHHh', 8, 0, 0, ID, 1)
        data = bytes('hi', 'ascii')
        # 2. Checksum ICMP packet using given function
        checksum = super().checksum(header + data)
        # 3. Insert checksum into packet
        header = struct.pack('bbHHh', 8, 0, checksum, ID, 1)
        print(header)
        # 4. Send packet using socket
        dataToSend = header + data
        icmpSocket.sendto(dataToSend,(destinationAddress, 1))
        # 5. Record time of sending
        return time.time()

    def doOnePing(self, destinationAddress, timeout):
        # 1. Create ICMP socket
        icmpSocket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        ID = int(random.random() * 65535)
        # 2. Call sendOnePing function
        timesent = self.sendOnePing(icmpSocket, destinationAddress, ID)
        # 3. Call receiveOnePing function
        timerecieved = self.receiveOnePing(icmpSocket, destinationAddress, ID, args.timeout)
        # 4. Close ICMP socket
        icmpSocket.close()
        # 5. Return total network delay
        print(timesent)
        print(timerecieved)
        return timerecieved - timesent

    def __init__(self, args):
        print('Ping to: %s...' % (args.hostname))
        # 1. Look up hostname, resolving it to an IP address
        destinationAddress = socket.gethostbyname(args.hostname)
        print(destinationAddress)
        if(args.count == None):
            args.count = 1
        for x in range(args.count):
        # 2. Call doOnePing function, approxim
        # ately every second
            totalNetworkDelay = self.doOnePing(destinationAddress, args.timeout)
            time.sleep(1)
        # 3. Print out the returned delay (and other relevant details) using the printOneResult method
            self.printOneResult(destinationAddress, self.packetLength, totalNetworkDelay*1000, 150) # Example use of printOneResult - complete as appropriate
        # 4. Continue this process until stopped


class Traceroute(NetworkApplication):
    
    flag = False #flag is true if echo reply message received
    packetLength = 0
    address = 0
    hostname = None

    def receiveOneRoute(self, icmpSocket, destinationAddress, ID, timeout):
        while True:
            ready = select.select([icmpSocket],[], [], timeout)
            if ready[0] == []:
                ##print("Error")
                return -1
            packet, address = icmpSocket.recvfrom(1024)
            self.packetLength = len(packet)
            self.address = address
            try:
                self.hostname = socket.gethostbyaddr(address[0])
            except socket.error:
                address = "Hostname unresolved"
            icmpHeader = packet[20:28]
            type, code, checksum, packetID, sequence = struct.unpack('bbHHh', icmpHeader)
            print(type)
            if(type == 0):
                self.flag = True
            break
        return time.time()

    def sendOneRoute(self, icmpSocket, destinationAddress, ID):
        # 1. Build ICMP header
        header = struct.pack('bbHHh', 8, 0, 0, ID, 1)
        data = bytes('hi', 'ascii')
        # 2. Checksum ICMP packet using given function
        checksum = super().checksum(header + data)
        # 3. Insert checksum into packet
        header = struct.pack('bbHHh', 8, 0, checksum, ID, 1)
        # 4. Send packet using socket
        dataToSend = header + data
        icmpSocket.sendto(dataToSend,(destinationAddress, 1))
        # 5. Record time of sending
        return time.time()

    def doOneRoute(self, destinationAddress, timeout, ttl):
        # 1. Create ICMP socket
        icmpSocket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        icmpSocket.setsockopt(socket.SOL_IP, socket.IP_TTL, ttl)
        ID = int(random.random() * 65535)
        timesent = self.sendOneRoute(icmpSocket, destinationAddress, ID)
        timerecieved = self.receiveOneRoute(icmpSocket, destinationAddress, ID, timeout)
        if timerecieved == -1:
            return -1
        icmpSocket.close
        return timerecieved - timesent


    def __init__(self, args):
        # Please ensure you print each result using the printOneResult method!
        print('Traceroute to: %s...' % (args.hostname))
        destinationAddress = socket.gethostbyname(args.hostname)
        for ttl in range(1,255):
            time = self.doOneRoute(destinationAddress, args.timeout, ttl)
            if time == -1:
                print("Packet lost with ttl", ttl)
            else:
                self.printOneResult(self.address[0], self.packetLength, time * 1000, ttl, self.hostname[0])
            if self.flag == True:
                break


class WebServer(NetworkApplication):

    def handleRequest(self, tcpSocket):
        print("we here")
        error404 = "HTTP/1.1 404 NOT FOUND\n\nError 404\n"
        # 1. Receive request message from the client on connection socket
        request = tcpSocket.recv(1024)
        print(request)
        split = request.split()
        print(split[0])
        print(split[1])
        # 2. Extract the path of the requested object from the message (second part of the HTTP header)
        # 3. Read the corresponding file from disk
        if(split[0] == b'GET' and split[1] == b'/index.html'):
            print("tru1")
            # 4. Store in temporary buffer
            file = open("index.html", "r")
            # 5. Send the correct HTTP response error
            tcpSocket.sendall(b'HTTP/1.1 200 OK\n')
            tcpSocket.sendall(b'Content-Type: text/html\n')
            tcpSocket.send(b'\r\n')
            # 6. Send the content of the file to the socket
            for line in file.readlines():
                tcpSocket.sendall(line.encode())
            file.close()
        else:
            print("error 404")
            tcpSocket.sendall(b'HTTP/1.1 404 NOT FOUND\n')
            tcpSocket.sendall(b'Content-Type: text/html\n')
            tcpSocket.send(b'\r\n')
            tcpSocket.send(b"""
                <html>
                    <body>
                        <h1>Error 404</h1> 
                    </body>
                </html>
            """)
        # 7. Close the connection socket
        tcpSocket.close()
        return

    def __init__(self, args):
        print('Web Server starting on port: %i...' % (args.port))
        # 1. Create server socket
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #makes sure address is reusable
        # 2. Bind the server socket to server address and server port
        server.bind(('127.0.0.1', args.port))
        # 3. Continuously listen for connections to server socket
        server.listen(5)
        # 4. When a connection is accepted, call handleRequest function, passing new connection socket (see https://docs.python.org/3/library/socket.html#socket.socket.accept)
        try:
            while True:
                (clientsocket, address) = server.accept()
                print(clientsocket)
                print(address)
                self.handleRequest(clientsocket)
        except KeyboardInterrupt:
            # 5. Close server socket if keyboard interrupt
            server.shutdown(socket.SHUT_RDWR)
            server.close()


class Proxy(NetworkApplication):

    def handleRequest(self, tcpSocket):
        # 1. Receive request message from the client on connection socket
        request = tcpSocket.recv(1024)
        split = request.split()
        url = split[1]
        url = str(url)
        httpPos = url.find("://")
        webserver = url[httpPos+3:len(url)-2]
        port = 80 #default port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        ##print(webserver)
        s.connect((webserver, port))
        s.sendall(request)
        data = s.recv(1024)
        ##print(data)
        tcpSocket.send(data) #send data back
        tcpSocket.close()
        return

    def __init__(self, args):
        print('Web Proxy starting on port: %i...' % (args.port))
        # 1. Create server socket
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #makes sure address is reusable
        # 2. Bind the server socket to server address and server port
        server.bind(('127.0.0.1', args.port))
        # 3. Continuously listen for connections to server socket
        server.listen(5)
        try:
            while True:
                (clientSocket, address) = server.accept()
                ##print(clientsocket)
                ##print(address)
                self.handleRequest(clientSocket)
        except KeyboardInterrupt:
            # 5. Close server socket if keyboard interrupt
            server.shutdown(socket.SHUT_RDWR)
            server.close()




if __name__ == "__main__":
    args = setupArgumentParser()
    args.func(args)
