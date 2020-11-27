import os
import sqlite3 
from sqlite3 import Error

class Database():
    def __init__(self):
        self.connection   = None
        self.DatabasePath = ""
    
    def CreateConnection(self, folder, dabase):
        if not os.path.exists(folder):
            os.mkdir(folder)
        self.DatabasePath = os.path.join(os.path.abspath(folder), dabase)
        try:
            self.connection = sqlite3.connect(self.DatabasePath)
        except Error as e:
            print(e)

    def CreateTables(self):
        Coils            = """CREATE TABLE IF NOT EXISTS Coils(ID INTEGER PRIMARY KEY, VALUE BOOLEAN);"""
        DiscretesInput   = """CREATE TABLE IF NOT EXISTS DiscretesInput(ID INT PRIMARY KEY, VALUE BOOLEAN);"""
        InputRegisters   = """CREATE TABLE IF NOT EXISTS InputRegisters(ID INT PRIMARY KEY, VALUE SMALLINT);"""
        HoldingRegisters = """CREATE TABLE IF NOT EXISTS HoldingRegisters(ID INT PRIMARY KEY, VALUE SMALLINT);"""
        Tables = [Coils, DiscretesInput, InputRegisters, HoldingRegisters]
        if self.connection is not None:
            for Table in Tables:
                try:
                    self.connection.cursor().execute(Table)
                except Error as e:
                    print(e)

    def InitializeTables(self):
        for i in range(1, 10000):
            self.connection.execute("""INSERT OR IGNORE INTO Coils(ID, VALUE) VALUES (?, ?)""", (i, 0))
        for i in range(10001, 20000):
            self.connection.execute("""INSERT OR IGNORE INTO DiscretesInput(ID, VALUE) VALUES (?, ?)""", (i, 0))
        for i in range(30001, 40000):
            self.connection.execute("""INSERT OR IGNORE INTO InputRegisters(ID, VALUE) VALUES (?, ?)""", (i, 0))
        for i in range(40001, 50000):
            self.connection.execute("""INSERT OR IGNORE INTO HoldingRegisters(ID, VALUE) VALUES (?, ?)""", (i, 0))
        self.connection.commit()

    def ResetCoils(self):
        for i in range(1, 10000):
            self.connection.execute("""UPDATE Coils SET VALUE=? WHERE ID=?""", (0, i))
        self.connection.commit()

    def ResetDiscretesInput(self):
        for i in range(10001, 20000):
            self.connection.execute("""UPDATE DiscretesInput SET VALUE=? WHERE ID=?""", (0, i))
        self.connection.commit()
    
    def ResetInputRegisters(self):
        for i in range(30001, 40000):
            self.connection.execute("""UPDATE InputRegisters SET VALUE=? WHERE ID=?""", (0, i))
        self.connection.commit()
    
    def ResetHoldingRegisters(self):
        for i in range(40001, 50000):
            self.connection.execute("""UPDATE HoldingRegisters SET VALUE=? WHERE ID=?""", (0, i))
        self.connection.commit()

    def InitializeDatabase(self, folder, database):
        db = Database()
        db.CreateConnection(folder, database)
        db.CreateTables()
        db.InitializeTables()
        return db