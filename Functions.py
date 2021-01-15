from tkinter import ttk
import tkinter as tk
import mysql.connector
import threading
import socket
import queue
import psutil
import copy
import math
import time
import sys
import os

Illegal_Function    = 0x01
Illegal_Data_Adress = 0x02
Illegal_Data_Value  = 0x03
Server_Failure      = 0x04
Server_Busy         = 0x06

Coils_Offset             = 0
Discretes_Input_Offset   = 10000
Input_Registers_Offset   = 30000
Holding_Registers_Offset = 40000

Cont_Catalin = [192, 168, 56, 1]
Parola_Catalin = ([1155, 6677])

class Database:
    def __init__(self, host, user, password):
        self.connection = mysql.connector.connect(host = host, user = user, password = password)
        cursor = self.connection.cursor()
        cursor.execute("CREATE  DATABASE IF NOT EXISTS ModbusTCP")
        self.connection = mysql.connector.connect(host = host, user = user, password = password, database = "ModbusTCP")
    
    def __CreateTables(self):
        cursor = self.connection.cursor()
        Coils            = "CREATE TABLE IF NOT EXISTS Coils(ID SMALLINT PRIMARY KEY, VALUE BOOLEAN)"
        DiscretesInput   = "CREATE TABLE IF NOT EXISTS DiscretesInput(ID INT PRIMARY KEY, VALUE BOOLEAN)"
        InputRegisters   = "CREATE TABLE IF NOT EXISTS InputRegisters(ID INT PRIMARY KEY, VALUE SMALLINT UNSIGNED)"
        HoldingRegisters = "CREATE TABLE IF NOT EXISTS HoldingRegisters(ID INT PRIMARY KEY, VALUE SMALLINT UNSIGNED)"
        Tables = [Coils, DiscretesInput, InputRegisters, HoldingRegisters]
        if self.connection is not None:
            for Table in Tables:
                try:
                     cursor.execute(Table)
                except Error as e:
                    print(e)
    
    def __InitializeTables(self):
        cursor = self.connection.cursor()
        for i in range(1, 250):
            cursor.execute("INSERT IGNORE INTO Coils(ID, VALUE) VALUES (%s, %s)", (i, 0))
        for i in range(10001, 10250):
            cursor.execute("INSERT IGNORE INTO DiscretesInput(ID, VALUE) VALUES (%s, %s)", (i, 0))
        for i in range(30001, 30250):
            cursor.execute("INSERT IGNORE INTO InputRegisters(ID, VALUE) VALUES (%s, %s)", (i, 0))
        for i in range(40001, 40250):
            cursor.execute("INSERT IGNORE INTO HoldingRegisters(ID, VALUE) VALUES (%s, %s)", (i, 0))
        self.connection.commit()

    def ResetCoils(self):
        cursor = self.connection.cursor()
        for i in range(1, 250):
            cursor.execute("UPDATE Coils SET VALUE = %s WHERE ID = %s", (0, i))
        self.connection.commit()

    def ResetDiscretesInput(self):
        cursor = self.connection.cursor()
        for i in range(10001, 10250):
            cursor.execute("UPDATE DiscretesInput SET VALUE = %s WHERE ID = %s", (0, i))
        self.connection.commit()
    
    def ResetInputRegisters(self):
        cursor = self.connection.cursor()
        for i in range(30001, 30250):
            cursor.execute("UPDATE InputRegisters SET VALUE = %s WHERE ID = %s", (0, i))
        self.connection.commit()
    
    def ResetHoldingRegisters(self):
        cursor = self.connection.cursor()
        for i in range(40001, 40250):
            cursor.execute("UPDATE HoldingRegisters SET VALUE = %s WHERE ID = %s", (0, i))
        self.connection.commit()

    def InitializeDatabase(self, host, user, password):
        db = Database(host, user, password)
        db.__CreateTables()
        db.__InitializeTables()
        return db

class Resources:
    def __init__(self):
        self.CPU_percent  = 0
        self.RAM_total    = 0
        self.RAM_percent  = 0
        self.DISK_total   = []
        self.DISK_percent = []

    def Update(self):
        self.CPU_percent  = psutil.cpu_percent(1)
        self.RAM_total    = psutil.virtual_memory().total/2**30
        self.RAM_percent  = psutil.virtual_memory().percent
        self.DISK_total   = list(psutil.disk_usage(i.device).total/2**30 for i in psutil.disk_partitions(False))
        self.DISK_percent = list(psutil.disk_usage(i.device).percent for i in psutil.disk_partitions(False))

class ADU:
    def __init__(self, request):
        self.TI    = request[0:2]
        self.PI    = request[2:4]
        self.L     = request[4:6]
        self.UI    = request[6:7]
        self.FC    = request[7:8]
        self.DATA  = request[8:6 + BytesToWord(self.L)]

    def Join(self):
        return self.TI + self.PI + self.L + self.UI + self.FC + self.DATA

    def Print(self):
        String = format(self.TI[0], '#04X')[2:] + format(self.TI[1], '#04X')[2:] + " " + format(self.PI[0], '#04X')[2:] + format(self.PI[1], '#04X')[2:] + " " + format(self.L[0], '#04X')[2:] + format(self.L[1], '#04X')[2:] + " " + format(self.UI[0], '#04X')[2:] + " " + format(self.FC[0], '#04X')[2:] + " "
        for i in range(len(self.DATA)):
            String =String + format(self.DATA[i], '#04X')[2:]
        return String

def BytesToWord(Bytes):
    return (Bytes[0] << 8) + Bytes[1]

def IntToBytes(Offset, Number, Dim):
    return (Offset + Number).to_bytes(Dim, 'big')
       
def BitsToBytes(Bits):
    pairs  = []
    result = []
    byte   = 0
    for _ in range(int(len(Bits)/8)):
        pairs.append(Bits[byte:byte + 8][::-1])
        byte = byte + 8
    for i in pairs:
        Map = map(int, i) 
        n = int(''.join(map(str, Map)), 2) 
        result.append(int('{:02x}'.format(n), 16))
    return bytes(result)

def BytesToBits(Register):
    String = list("{0:b}".format(Register).zfill(8))
    List = []
    for i in range(8):
        List.append(ord(String[i]) - ord('0'))
    return List[::-1] 

def StringListToIntList(StringList):
    IntList = []
    for i in range(len(StringList)):
        IntList.append(int(StringList[i]))
    return IntList

def GetProcesses():
    processes = []
    for process in psutil.process_iter():
            try:
                processes.append(list(process.as_dict(attrs = ['name']).values()))
            except psutil.NoSuchProcess:
                pass
    def ListOfListsToList(ListOfLists):
        List = []
        for Sublist in ListOfLists:
            for Value in Sublist:
                List.append(Value.lower())
        return List
    return ListOfListsToList(processes)