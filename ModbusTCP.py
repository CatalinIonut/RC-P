from Database  import Database
from Functions import *
import socket
import queue
import copy

Illegal_Function    = 0x01
Illegal_Data_Adress = 0x02
Illegal_Data_Value  = 0x03
Server_Failure      = 0x04
Server_Busy         = 0x06

Coils_Offset             = 0
Discretes_Input_Offset   = 10000
Input_Registers_Offset   = 30000
Holding_Registers_Offset = 40000

class ClientModbusTCP:
    def __init__(self):
        self.Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.Database = Database.InitializeDatabase(self, "Dadabase", "Dadabase.db")
    
    def Bind(self):
        self.Socket.bind((socket.gethostbyname(socket.gethostname()), 502))

    def Recive(self):
        self.Socket.listen(1)
        print("[LISTENING]\n")
        connection, adress = self.Socket.accept()
        with connection:
            print(f"[CONNECTED BY {adress[0]}]\n")
            while True:
                message  = connection.recv(1024)
                if not message:
                    print(f"[DISCONNECTED FROM {adress[0]}]\n")
                    self.Recive()
                request = ADU(message)
                print(f"<<<  ", end = "")
                request.Print()
                respond = self.Respond(request)
                print(f">>>  ", end = "")
                respond.Print()
                connection.sendall(respond.Join())

    def __Read_Coil_Status(self, request):
        response        = copy.deepcopy(request)
        start_adress    = BytesToWord(request.DATA[0:2])
        number_of_coils = BytesToWord(request.DATA[2:4])
        first_coil      = start_adress + Coils_Offset
        last_coil       = first_coil + number_of_coils
        coils           = []
        for i in range(first_coil, last_coil):
            coils.append(self.Database.connection.execute("""SELECT VALUE FROM Coils WHERE ID=?""", (i,)).fetchall()[0][0])
        for _ in range(8 - (len(coils) % 8)):
            coils.append(0)
        result        = bytes([int(len(coils)/8)])
        result        = result + BitsToBytes(coils)
        response.L    = IntToBytes(2, len(result), 2)
        response.DATA = result
        return response

    def __Read_Discrete_Inputs(self, request):
        response        = copy.deepcopy(request)
        start_adress    = BytesToWord(request.DATA[0:2])
        number_of_di    = BytesToWord(request.DATA[2:4])
        first_di        = start_adress + Discretes_Input_Offset
        last_di         = first_di + number_of_di
        discretes_input = []
        for i in range(first_di, last_di):
            discretes_input.append(self.Database.connection.execute("""SELECT VALUE FROM DiscretesInput WHERE ID=?""", (i,)).fetchall()[0][0])  
        for _ in range(8 - (len(discretes_input) % 8)):
            discretes_input.append(0)
        result        = bytes([int(len(discretes_input)/8)])
        result        = result + BitsToBytes(discretes_input)
        response.L    = IntToBytes(2, len(result), 2)
        response.DATA = result
        return response

    def __Read_Holding_Registers(self, request):
        response          = copy.deepcopy(request)
        start_adress      = BytesToWord(request.DATA[0:2])
        number_of_hr      = BytesToWord(request.DATA[2:4])
        first_hr          = start_adress + Holding_Registers_Offset
        last_hr           = first_hr + number_of_hr
        result            = bytes([number_of_hr*2])
        holding_registers = []
        for i in range(first_hr, last_hr):
            holding_registers.append(self.Database.connection.execute("""SELECT VALUE FROM HoldingRegisters WHERE ID=?""", (i,)).fetchall()[0][0])
        for i in range(len(holding_registers)):
            result = result + IntToBytes(0, holding_registers[i], 2)
        response.L    = IntToBytes(2, len(result), 2)
        response.DATA = result
        return response

    def __Read_Input_Registers(self, request):
        response        = copy.deepcopy(request)
        start_adress    = BytesToWord(request.DATA[0:2])
        number_of_ir    = BytesToWord(request.DATA[2:4])
        first_ir        = start_adress + Input_Registers_Offset
        last_ir         = first_ir + number_of_ir
        result          = bytes([number_of_ir*2])
        input_registers = []
        for i in range(first_ir, last_ir):
            input_registers.append(self.Database.connection.execute("""SELECT VALUE FROM InputRegisters WHERE ID=?""", (i,)).fetchall()[0][0])
        for i in range(len(input_registers)):
            result = result + IntToBytes(0, input_registers[i], 2)
        response.L    = IntToBytes(2, len(result), 2)
        response.DATA = result
        return response

    def __Force_Single_Coil(self, request):
        response     = copy.deepcopy(request)
        start_adress = BytesToWord(request.DATA[0:2])
        value        = BytesToWord(request.DATA[2:4])
        adress_coil  = start_adress + Coils_Offset
        if(value == 0xFF00):
            self.Database.connection.execute("""UPDATE Coils SET VALUE=? WHERE ID=?""", (1, adress_coil))
        elif(value == 0x0000):
            self.Database.connection.execute("""UPDATE Coils SET VALUE=? WHERE ID=?""", (0, adress_coil))
        self.Database.connection.commit()
        return response

    def __Write_Single_Register(self, request):
        response     = copy.deepcopy(request)
        start_adress = BytesToWord(request.DATA[0:2])
        value        = BytesToWord(request.DATA[2:4])
        adress_hr    = start_adress + Holding_Registers_Offset
        self.Database.connection.execute("""UPDATE HoldingRegisters SET VALUE=? WHERE ID=?""", (value, adress_hr))
        self.Database.connection.commit()
        return response

    def __Force_Multiple_Coils(self, request):
        response      = copy.deepcopy(request)
        start_adress  = BytesToWord(request.DATA[0:2])
        no_coils      = BytesToWord(request.DATA[2:4])
        bytes_after   = request.DATA[4]
        first_coil    = start_adress + Coils_Offset
        registers     = []
        coils         = []
        for i in range(5, 5 + bytes_after):
            registers.append(request.DATA[i])
        for i in range(len(registers)):
            coils = coils + (BytesToBits(registers[i]))
        for i in range(no_coils):
            self.Database.connection.execute("""UPDATE Coils SET VALUE=? WHERE ID=?""", (coils[i], first_coil + i))
        self.Database.connection.commit()
        response.L    = IntToBytes(2, 4, 2)
        response.DATA = request.DATA[0:4]
        return response

    def __Write_Multiple_Registers(self, request):
        response          = copy.deepcopy(request)
        start_adress      = BytesToWord(request.DATA[0:2])
        no_hr             = BytesToWord(request.DATA[2:4])
        bytes_after       = request.DATA[4]
        first_hr          = start_adress + Holding_Registers_Offset
        holding_registers = []
        for i in range(5, 5 + bytes_after):
            holding_registers.append(request.DATA[i])
        for i in range(no_hr):
            self.Database.connection.execute("""UPDATE HoldingRegisters SET VALUE=? WHERE ID=?""", (BytesToWord(holding_registers[(i*2):(i*2 + 2)]), first_hr + i))
        self.Database.connection.commit()
        response.L    = IntToBytes(2, 4, 2)
        response.DATA = request.DATA[0:4]
        return response
   
    def __Illegal_Function(self, request):
        function  = request.FC[0]
        if function in [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x0F, 0x10]:
            return None
        else:
            response      = copy.deepcopy(request)
            response.FC   = bytes([response.FC[0] + 0x80])
            response.DATA = bytes([Illegal_Function])
            return response
    
    def __Illegal_Data_Adress(self, request):
        function = request.FC[0]
        if function in [0x01, 0x02, 0x03, 0x04, 0x0F, 0x10]:
            start_adress       = BytesToWord(request.DATA[0:2])
            number_of_coils    = BytesToWord(request.DATA[2:4])
            if (1 <= start_adress < 9999) and (1 <= (start_adress + number_of_coils) <= 9999):
                return None
            else:
                response      = copy.deepcopy(request)
                response.FC   = bytes([response.FC[0] + 0x80])
                response.DATA = bytes([Illegal_Data_Adress])
                return response

        if function in [0x05, 0x06]:
            start_adress = BytesToWord(request.DATA[0:2])
            if (1 <= start_adress < 9999):
                return None
            else:
                response      = copy.deepcopy(request)
                response.FC   = bytes([response.FC[0] + 0x80])
                response.DATA = bytes([Illegal_Data_Adress])
                return response

    def __Illegal_Data_Value(self, request):
        function = request.FC[0]
        if function in [0x01, 0x02]:
            quantity = BytesToWord(request.DATA[2:4])
            if 0x01 <= quantity <= 0x07D0:
                return None
            else:
                response      = copy.deepcopy(request)
                response.FC   = bytes([response.FC[0] + 0x80])
                response.DATA = bytes([Illegal_Data_Value])
                return response
        
        if function in [0x03, 0x04]:
            quantity = BytesToWord(request.DATA[2:4])
            if 0x01 <= quantity <= 0x007D:
                return None
            else:
                response      = copy.deepcopy(request)
                response.FC   = bytes([response.FC[0] + 0x80])
                response.DATA = bytes([Illegal_Data_Value])
                return  response
        
        if function == 0x05:
            value = BytesToWord(request.DATA[2:4])
            if value in [0x0000, 0xFF00]:
                return None
            else:
                response      = copy.deepcopy(request)
                response.FC   = bytes([response.FC[0] + 0x80])
                response.DATA = bytes([Illegal_Data_Value])
                return  response

        if function == 0x06:
            value = BytesToWord(request.DATA[2:4])
            if 0x0000 <= value <= 0xFFFF:
                return None
            else:
                response      = copy.deepcopy(request)
                response.FC   = bytes([response.FC[0] + 0x80])
                response.DATA = bytes([Illegal_Data_Value])
                return  response
        
        if function == 0x0F:
            quantity    = BytesToWord(request.DATA[2:4])
            bytes_after = request.DATA[4]
            if (0x01 <= quantity <=0x07B0) and (bytes_after == (int(quantity/8) + (quantity%8 > 0))):
                return None
            else:
                response      = copy.deepcopy(request)
                response.FC   = bytes([response.FC[0] + 0x80])
                response.DATA = bytes([Illegal_Data_Value])
                return  response

        if function == 0x10:
            quantity    = BytesToWord(request.DATA[2:4])
            bytes_after = request.DATA[4]
            if (0x01 <= quantity <= 0x007B) and (bytes_after == quantity*2):
                return None
            else:
                response      = copy.deepcopy(request)
                response.FC   = bytes([response.FC[0] + 0x80])
                response.DATA = bytes([Illegal_Data_Value])
                return  response
    
    def __Server_Failure(self, request):
        return None
    
    def __Server_Busy(self, request):
        return None

    def Respond(self, request):
        exception = self.Check(request)
        if exception == None:
            return {
                0x01: lambda: self.__Read_Coil_Status(request),
                0x02: lambda: self.__Read_Discrete_Inputs(request),
                0x03: lambda: self.__Read_Holding_Registers(request),
                0x04: lambda: self.__Read_Input_Registers(request),
                0x05: lambda: self.__Force_Single_Coil(request),
                0x06: lambda: self.__Write_Single_Register(request),
                0x0F: lambda: self.__Force_Multiple_Coils(request),
                0x10: lambda: self.__Write_Multiple_Registers(request)
            }.get(request.FC[0], lambda: None)()
        else:
            return exception

    def Check(self, request):
        exception = self.__Illegal_Function(request)
        if exception != None:
            return exception
        exception = self.__Illegal_Data_Adress(request)
        if exception != None:
            return exception
        exception = self.__Illegal_Data_Value(request)
        if exception != None:
            return exception
        return None

class ADU:
    def __init__(self, request):
        self.TI    = request[0:2]
        self.PI    = request[2:4]
        self.L     = request[4:6]
        self.UI    = request[6:7]
        self.FC    = request[7:8]
        self.DATA  = request[8:6 + ((self.L[0] << 8) + self.L[1])]

    def Join(self):
        return self.TI + self.PI + self.L + self.UI + self.FC + self.DATA

    def Print(self):
        print(format(self.TI[0], '#04X')[2:], format(self.TI[1], '#04X')[2:], " ", format(self.PI[0], '#04X')[2:], format(self.PI[1], '#04X')[2:], " ", format(self.L[0], '#04X')[2:], format(self.L[1], '#04X')[2:], " ", format(self.UI[0], '#04X')[2:], " ", format(self.FC[0], '#04X')[2:], " ", end = " ")
        for i in range(len(self.DATA)):
            print(format(self.DATA[i], '#04X')[2:], end = " ")
        print()

def main():
    Aplicatie = True
    DeMana    = not(Aplicatie)
    Read      = False
    Write     = not(Read)
    if Aplicatie:
        Client = ClientModbusTCP()
        Client.Bind()
        Client.Recive()
    if DeMana:
        Client = ClientModbusTCP()
        r1  = bytes([0x00, 0x01, 0x00, 0x00, 0x00, 0x06, 0x00, 0x01, 0x00, 0x13, 0x07, 0xD1])
        r2  = bytes([0x00, 0x02, 0x00, 0x00, 0x00, 0x06, 0x00, 0x02, 0x00, 0xC4, 0x00, 0x16])
        r3  = bytes([0x00, 0x03, 0x00, 0x00, 0x00, 0x06, 0x00, 0x03, 0x00, 0x6B, 0x00, 0x03])
        r4  = bytes([0x00, 0x04, 0x00, 0x00, 0x00, 0x06, 0x00, 0x04, 0x00, 0x08, 0x00, 0x01])
        r5  = bytes([0x00, 0x01, 0x00, 0x00, 0x00, 0x06, 0x00, 0x05, 0x00, 0x01, 0xFF, 0x00])
        r6  = bytes([0x00, 0x02, 0x00, 0x00, 0x00, 0x06, 0x00, 0x06, 0x00, 0x01, 0x00, 0xAA])
        r15 = bytes([0x00, 0x03, 0x00, 0x00, 0x00, 0x0C, 0x00, 0x0F, 0x00, 0x13, 0x00, 0x25, 0x05, 0xCD, 0x6B, 0xB2, 0x0E, 0x1B])
        r16 = bytes([0x00, 0x04, 0x00, 0x00, 0x00, 0x0E, 0x00, 0x10, 0x00, 0x6B, 0x00, 0x03, 0x06, 0xAE, 0x41, 0x56, 0x52, 0x43, 0x40])
        requests_read  = [r1, r2, r3, r4]
        requests_write = [r5, r6, r15, r16]
        if Read:
            for i in range(len(requests_read)):
                request = ADU(requests_read[i])
                request.Print()
                Client.Respond(request).Print()
                print()
        if Write:
            for i in range(len(requests_write)):
                request = ADU(requests_write[i])
                request.Print()
                Client.Respond(request).Print()
                print()

main()