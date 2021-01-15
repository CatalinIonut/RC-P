from Functions import *

class Application:
    def __init__(self):
        self.__Socket          = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__Database        = Database.InitializeDatabase(self, host = "localhost", user = "root", password = "root")
        self.__Resources       = Resources()
        self.__ServerFailure   = False
        self.__ServerBusy      = False
        self.__Ready           = False
        self.__GUIThread       = threading.Thread(target = self.__GUI)
        self.__ListeningThread = threading.Thread(target = self.__ModbusTCP)
        self.__ResourcesThread = threading.Thread(target = self.__UpdateResources)
    
    def __Bind(self):
        self.__Socket.bind((socket.gethostbyname(socket.gethostname()), 502))
    
    def __Listen(self, dimension):
        self.__Socket.listen(dimension)
    
    def __Accept(self):
        return self.__Socket.accept()
        
    def __Close(self):
        self.__Socket.close()

    def __CreateAccount(self, ip, password):
        cursor = self.__Database.connection.cursor()
        cursor.execute("SELECT VALUE FROM InputRegisters WHERE ID = %s", (30099,))
        no_accounts    = cursor.fetchall()[0][0]
        new_account    = StringListToIntList(ip.split(".")) + list(password)
        accounts_1     = []
        accounts       = []
        already_exists = False
        for i in range(30100, 30100 + 8*no_accounts):
            cursor.execute("SELECT VALUE FROM InputRegisters WHERE ID = %s", (i,))
            accounts_1.append(cursor.fetchall()[0][0])
        for i in range(no_accounts):
            accounts.append([])
            for j in range(8):
                accounts[i].append(accounts_1[i*8 + j])
        for i in range(no_accounts):
            if accounts[i][0:4] == new_account[0:4]:
                already_exists = True
        if already_exists:
            print("The account already exists!")
            return "The account already exists!"
        else:
            for i, j in zip(range(30100 + 8*no_accounts, 30100 + 8*(no_accounts + 1)), range(8)):
                cursor.execute("UPDATE InputRegisters SET VALUE = %s WHERE ID = %s", (new_account[j], i))
            cursor.execute("UPDATE InputRegisters SET VALUE = %s WHERE ID = %s""", (no_accounts + 1, 30099))
            self.__Database.connection.commit()
            print("The account has been created successfully!")
            return "The account has been created successfully!"
    
    def __CheckAccount(self, ip, password):
        cursor = self.__Database.connection.cursor()
        cursor.execute("SELECT VALUE FROM InputRegisters WHERE ID = %s", (30099,))
        no_accounts = cursor.fetchall()[0][0]
        account     = StringListToIntList(ip.split(".")) + list(password)
        accounts_1  = []
        accounts    = []
        for i in range(30100, 30100 + 8*no_accounts):
            cursor.execute("SELECT VALUE FROM InputRegisters WHERE ID = %s", (i,))
            accounts_1.append(cursor.fetchall()[0][0])
        for i in range(no_accounts):
            accounts.append([])
            for j in range(8):
                accounts[i].append(accounts_1[i*8 + j])      
        if account in accounts:
            return True
        else:
            return False

    def __Recive(self, connection, adress):
        connected = False
        with connection:
            self.Console.insert(tk.END, f"[TRYING TO CONNECT TO {adress[0]}]\n\n")
            print(f"[TRYING TO CONNECT TO {adress[0]}]\n")
            while True:
                message = connection.recv(1024)
                if not message:
                    if connected:
                        self.Console.insert(tk.END, f"[DISCONNECTED FROM {adress[0]}]\n\n")
                        print(f"[DISCONNECTED FROM {adress[0]}]\n")
                    else:
                        self.Console.insert(tk.END, f"[FAILED TO CONNECT TO {adress[0]}]\n\n")
                        print(f"[FAILED TO CONNECT TO {adress[0]}]\n")
                    break
                request = ADU(message)
                if not connected:
                    connected = self.__CheckAccount(ip = adress[0], password = request.DATA)
                    if connected:
                        self.Console.insert(tk.END, f"[CONNECTED BY {adress[0]}]\n\n")
                        print(f"[CONNECTED BY {adress[0]}]\n")
                    continue
                self.Console.insert(tk.END, f"<<< [{adress[0]}]  {request.Print()}\n")
                print(f"<<< [{adress[0]}]  {request.Print()}")
                respond = self.__Respond(request)
                self.Console.insert(tk.END, f">>> [{adress[0]}]  {respond.Print()}\n\n")
                print(f">>> [{adress[0]}]  {respond.Print()}\n")
                connection.sendall(respond.Join())
            connection.close()

    def __Read_Coil_Status(self, request):
        response        = copy.deepcopy(request)
        start_adress    = BytesToWord(request.DATA[0:2])
        number_of_coils = BytesToWord(request.DATA[2:4])
        first_coil      = start_adress + Coils_Offset
        last_coil       = first_coil + number_of_coils
        coils           = []
        cursor          = self.__Database.connection.cursor()
        for i in range(first_coil, last_coil):
            cursor.execute("SELECT VALUE FROM Coils WHERE ID = %s", (i,))
            coils.append(cursor.fetchall()[0][0])
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
        cursor          = self.__Database.connection.cursor()
        for i in range(first_di, last_di):
            cursor.execute("SELECT VALUE FROM DiscretesInput WHERE ID = %s", (i,))
            discretes_input.append(cursor.fetchall()[0][0])  
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
        cursor            = self.__Database.connection.cursor()
        for i in range(first_hr, last_hr):
            cursor.execute("SELECT VALUE FROM HoldingRegisters WHERE ID = %s", (i,))
            holding_registers.append(cursor.fetchall()[0][0])
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
        cursor          = self.__Database.connection.cursor()
        for i in range(first_ir, last_ir):
            cursor.execute("SELECT VALUE FROM InputRegisters WHERE ID = %s", (i,))
            input_registers.append(cursor.fetchall()[0][0])
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
        cursor       = self.__Database.connection.cursor()
        if(value == 0xFF00):
            cursor.execute("UPDATE Coils SET VALUE = %s WHERE ID = %s", (1, adress_coil))
        elif(value == 0x0000):
            cursor.execute("UPDATE Coils SET VALUE = %s WHERE ID = %s", (0, adress_coil))
        self.__Database.connection.commit()
        return response

    def __Write_Single_Register(self, request):
        response     = copy.deepcopy(request)
        start_adress = BytesToWord(request.DATA[0:2])
        value        = BytesToWord(request.DATA[2:4])
        adress_hr    = start_adress + Holding_Registers_Offset
        cursor       = self.__Database.connection.cursor()
        cursor.execute("UPDATE HoldingRegisters SET VALUE = %s WHERE ID = %s", (value, adress_hr))
        self.__Database.connection.commit()
        return response

    def __Force_Multiple_Coils(self, request):
        response      = copy.deepcopy(request)
        start_adress  = BytesToWord(request.DATA[0:2])
        no_coils      = BytesToWord(request.DATA[2:4])
        bytes_after   = request.DATA[4]
        first_coil    = start_adress + Coils_Offset
        registers     = []
        coils         = []
        cursor        = self.__Database.connection.cursor()
        for i in range(5, 5 + bytes_after):
            registers.append(request.DATA[i])
        for i in range(len(registers)):
            coils = coils + (BytesToBits(registers[i]))
        for i in range(no_coils):
            cursor.execute("UPDATE Coils SET VALUE = %s WHERE ID = %s", (coils[i], first_coil + i))
        self.__Database.connection.commit()
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
        cursor            = self.__Database.connection.cursor()
        for i in range(5, 5 + bytes_after):
            holding_registers.append(request.DATA[i])
        for i in range(no_hr):
            cursor.execute("UPDATE HoldingRegisters SET VALUE = %s WHERE ID = %s", (BytesToWord(holding_registers[(i*2):(i*2 + 2)]), first_hr + i))
        self.__Database.connection.commit()
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
            number_of_data     = BytesToWord(request.DATA[2:4])
            if (0x01 <= start_adress <= 0xF9) and (0x01 <= (start_adress + number_of_data - 1) <= 0xF9):
                return None
            else:
                response      = copy.deepcopy(request)
                response.FC   = bytes([response.FC[0] + 0x80])
                response.DATA = bytes([Illegal_Data_Adress])
                return response

        if function in [0x05, 0x06]:
            start_adress = BytesToWord(request.DATA[0:2])
            if (0x01 <= start_adress <= 0xF9):
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
            if 0x01 <= quantity <= 0xF9:
                return None
            else:
                response      = copy.deepcopy(request)
                response.FC   = bytes([response.FC[0] + 0x80])
                response.DATA = bytes([Illegal_Data_Value])
                return response
        
        if function in [0x03, 0x04]:
            quantity = BytesToWord(request.DATA[2:4])
            if 0x01 <= quantity <= 0x7D:
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
            if (0x01 <= quantity <= 0xF9) and (bytes_after == (int(quantity/8) + (quantity%8 > 0))):
                return None
            else:
                response      = copy.deepcopy(request)
                response.FC   = bytes([response.FC[0] + 0x80])
                response.DATA = bytes([Illegal_Data_Value])
                return  response

        if function == 0x10:
            quantity    = BytesToWord(request.DATA[2:4])
            bytes_after = request.DATA[4]
            if (0x01 <= quantity <= 0x7B) and (bytes_after == quantity*2):
                return None
            else:
                response      = copy.deepcopy(request)
                response.FC   = bytes([response.FC[0] + 0x80])
                response.DATA = bytes([Illegal_Data_Value])
                return  response
    
    def __Server_Failure(self, request):
        if self.__ServerFailure:
            self.__ServerFailure = False
            response      = copy.deepcopy(request)
            response.FC   = bytes([response.FC[0] + 0x80])
            response.DATA = bytes([Server_Failure])
            return response
        else:
            return None
    
    def __Server_Busy(self, request):
        if self.__ServerBusy:
            self.__ServerBusy = False
            time.sleep(5)
            response      = copy.deepcopy(request)
            response.FC   = bytes([response.FC[0] + 0x80])
            response.DATA = bytes([Server_Busy])
            return response
        else:
            return None

    def __Respond(self, request):
        exception = self.__Check(request)
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

    def __Check(self, request):
        exception = self.__Illegal_Function(request)
        if exception != None:
            return exception
        exception = self.__Illegal_Data_Adress(request)
        if exception != None:
            return exception
        exception = self.__Illegal_Data_Value(request)
        if exception != None:
            return exception
        exception = self.__Server_Failure(request)
        if exception != None:
            return exception
        exception = self.__Server_Busy(request)
        if exception != None:
            return exception
        return None

    def __SetServerFailure(self):
        self.__ServerFailure = True
    
    def __SetServerBusy(self):
        self.__ServerBusy = True

    def __GUI(self):
        self.root = tk.Tk()
        self.root.title("Client ModbusTCP")

        ###Tab1
        self.MainFrame = tk.LabelFrame(self.root)
        self.MainFrame.config(background='#000000', font='{Consolas} 40 {bold}', foreground='#ffffff', height='500', labelanchor='n', padx='5', pady='5', relief='ridge', takefocus=False, text='Client ModbusTCP', width='750')
        self.MainFrame.pack(side='top')

        self.ExceptionsFrame = tk.LabelFrame(self.MainFrame)
        self.ExceptionsFrame.config(highlightbackground='#000000', highlightcolor='#000000', labelanchor='n', relief='flat', text='For The Next Request', width='1000', background='#000000', font='{Consolas} 20 {bold}', foreground='#ffffff', height='200')
        self.ExceptionsFrame.grid(padx='0', pady='10', row='0')

        self.ServerFailureButton = tk.Button(self.ExceptionsFrame, command=self.__SetServerFailure)
        self.ServerFailureButton.config(activebackground='#0080ff', background='#a4d1ff', font='{Consolas} 12 {bold}', text='Server Failure', width='14')
        self.ServerFailureButton.grid(column='0', padx='5', pady='5')

        self.ServerBusyButton = tk.Button(self.ExceptionsFrame, command=self.__SetServerBusy)
        self.ServerBusyButton.config(activebackground='#ff80ff', background='#ffbbff', font='{Consolas} 12 {bold}', text='Server Busy', width='14')
        self.ServerBusyButton.grid(column='1', padx='5', pady='5', row='0')
        
        self.CreateAccoutnFrame = tk.LabelFrame(self.MainFrame)
        self.CreateAccoutnFrame.config(background='#000000', font='{Consolas} 20 {bold}', foreground='#ffffff', height='200', text='Create An Account', width='250', highlightbackground='#000000', highlightcolor='#000000', labelanchor='n', relief='flat')
        self.CreateAccoutnFrame.grid(column='0', padx='0', pady='10', row='1')

        self.IpFrame = tk.LabelFrame(self.CreateAccoutnFrame)
        self.IpFrame.config(background='#000000', font='{Consolas} 12 {}', foreground='#ffffff', height='200', labelanchor='n', text='Enter The IP', width='200')
        self.IpFrame.grid()

        self.IPInput = tk.Entry(self.IpFrame)
        self.IPInput.config(font='{Consolas} 10 {bold}', relief='flat', state='normal', width='25')
        self.IPInput.grid(padx='5', pady='5')
        
        self.PasswordFrame = tk.LabelFrame(self.CreateAccoutnFrame)
        self.PasswordFrame.config(background='#000000', font='{Consolas} 12 {}', foreground='#ffffff', height='200',labelanchor='n', text='Enter The Password', width='200')
        self.PasswordFrame.grid(column='0', row='1')

        self.PasswordInput = tk.Entry(self.PasswordFrame)
        self.PasswordInput.config(font='{Consolas} 10 {bold}', width='25', show='•')
        self.PasswordInput.grid(padx='5', pady='5')
        
        self.CreateButtonFrame = tk.Frame(self.CreateAccoutnFrame)
        self.CreateButtonFrame.config(background='#000000', height='200', width='200')
        self.CreateButtonFrame.grid(column='0', row='2')

        self.CreateButton = tk.Button(self.CreateButtonFrame, command=self.__Submit)
        self.CreateButton.config(activebackground='#ff0000', background='#ff4848', font='{Consolas} 12 {bold}', text='Create')
        self.CreateButton.grid(pady='5')
        
        self.MessageFrame = tk.Frame(self.CreateAccoutnFrame)
        self.MessageFrame.config(background='#000000', height='200', width='300')
        self.MessageFrame.grid(column='0', row='3')

        self.MessageLabel = tk.Label(self.MessageFrame)
        self.MessageLabel.config(background='#000000', font='{Consolas} 12 {bold}', foreground='#ffffff', width='100')
        self.MessageLabel.pack(side='top')
        
        self.ConsoleFrame = tk.LabelFrame(self.MainFrame)
        self.ConsoleFrame.config(background='#000000', font='{Courier New} 20 {bold}', foreground='#ffffff', height='200', width='200', highlightbackground='#000000', highlightcolor='#000000', labelanchor='n', relief='flat')
        self.ConsoleFrame.grid(column='0', padx='10', pady='10', row='5')

        self.Console = tk.Text(self.ConsoleFrame)
        self.Console.config(autoseparators='false', background='#000000', blockcursor='false', borderwidth='10', font='{Consolas} 10 {bold}', foreground='#ffffff', height='20', insertborderwidth='10', insertunfocussed='none', relief='ridge', selectbackground='#ffffff', selectforeground='#80ffff', setgrid='true', tabstyle='wordprocessor', takefocus=False, width='125', wrap='none')
        self.Console.grid(padx='0')
        
        self.ResourcesFrame = tk.LabelFrame(self.MainFrame)
        self.ResourcesFrame.config(background='#000000', font='{Consolas} 20 {bold}', foreground='#ffffff', height='200', labelanchor='n', relief='flat', text='Resources', width='200')
        self.ResourcesFrame.grid(column='0', row='2')
        
        self.CPUFrame = tk.LabelFrame(self.ResourcesFrame)
        self.CPUFrame.config(background='#000000', font='{Consolas} 12 {}', foreground='#ffffff', height='200',labelanchor='n', text='CPU Usage', width='200')
        self.CPUFrame.grid(padx='5')

        self.CPUusageLabel = tk.Label(self.CPUFrame)
        self.CPUusageLabel.config(background='#000000', font='{Consolas} 12 {}', foreground='#ffffff', width='10')
        self.CPUusageLabel.pack(side='top')
        
        self.RAMFrame = tk.LabelFrame(self.ResourcesFrame)
        self.RAMFrame.config(background='#000000', font='{Consolas} 12 {}', foreground='#ffffff', height='200', labelanchor='n', text='RAM Usage', width='200')
        self.RAMFrame.grid(column='1', padx='5', row='0')
        
        self.RAMusageLabel = tk.Label(self.RAMFrame)
        self.RAMusageLabel.config(background='#000000', font='{Consolas} 12 {}', foreground='#ffffff', width='10')
        self.RAMusageLabel.pack(side='top')

        self.ProcessFrame = tk.LabelFrame(self.MainFrame)
        self.ProcessFrame.config(background='#000000', font='{Consolas} 12 {}', foreground='#ffffff', height='200', relief='flat')
        self.ProcessFrame.config(labelanchor='n', text='Enter A Process', width='200')
        self.ProcessFrame.grid(column='0', padx='5', row='3')

        self.ProcessEntry = tk.Entry(self.ProcessFrame)
        self.ProcessEntry.config(font='{Consolas} 10 {}', foreground='#000000', width='30')
        self.ProcessEntry.grid()

        self.CreateButtonProcess = tk.Button(self.ProcessFrame, command=self.__AddProcessToWatch)
        self.CreateButtonProcess.config(activebackground='#ff0000', background='#ff4848', font='{Consolas} 12 {bold}', text='Create')
        self.CreateButtonProcess.grid(column='0', pady='5', row='1')
        
        self.MessageFrameProcess = tk.Frame(self.MainFrame)
        self.MessageFrameProcess.config(background='#000000', height='200', width='200')
        self.MessageFrameProcess.grid(column='0', row='4')

        self.MessageLabelProcess = tk.Label(self.MessageFrameProcess)
        self.MessageLabelProcess.config(background='#000000', font='{Consolas} 12 {bold}', foreground='#ffffff', width='35')
        self.MessageLabelProcess.pack(side='top')
        
        self.__Ready = True
        self.root.mainloop()
        self.__Close()

    def __ModbusTCP(self):
        while True:
            if self.__Ready:
                break
        self.__Bind() 
        self.__Listen(5)
        self.Console.insert(tk.END, "[LISTENING]\n\n")
        print("[LISTENING]\n")
        while True:
            try:
                connection, adress = self.__Accept()
            except:
                print("Socket closed!")
                break
            try:
                threading.Thread(target = self.__Recive, args = (connection, adress)).start()
            except:
                print(f"Error to make a connection to {adress[0]}")

    def __UpdateResources(self):
        while True:
            if self.__Ready:
                break
        while self.__GUIThread.is_alive():
            if not self.__GUIThread.is_alive():
                break
            cursor = self.__Database.connection.cursor()
            self.__Resources.Update()
            cursor.execute("UPDATE InputRegisters SET VALUE = %s WHERE ID = %s", (math.ceil(self.__Resources.CPU_percent), Input_Registers_Offset + 1))
            cursor.execute("UPDATE InputRegisters SET VALUE = %s WHERE ID = %s", (math.ceil(self.__Resources.RAM_total), Input_Registers_Offset + 2))
            cursor.execute("UPDATE InputRegisters SET VALUE = %s WHERE ID = %s", (math.ceil(self.__Resources.RAM_percent), Input_Registers_Offset + 3))
            i = 4
            for ceva in self.__Resources.DISK_total:
                cursor.execute("UPDATE InputRegisters SET VALUE = %s WHERE ID = %s", (math.ceil(ceva), Input_Registers_Offset + i))
                i = i + 2
            i = 5
            for ceva in self.__Resources.DISK_percent:
                cursor.execute("UPDATE InputRegisters SET VALUE = %s WHERE ID = %s", (math.ceil(ceva), Input_Registers_Offset + i))
                i = i + 2
            self.CPUusageLabel.config(text=str(self.__Resources.CPU_percent) + '%')
            self.RAMusageLabel.config(text=str(self.__Resources.RAM_percent) + '%')
            processeswatch = open("Processes.txt", "r").read().split('\n')
            processeswatch = processeswatch[:len(processeswatch) - 1]
            if '' in processeswatch:
                processeswatch.remove('')
            processes = GetProcesses()
            i         = Discretes_Input_Offset + 1
            for process in processeswatch:
                if process in processes:
                    cursor.execute("UPDATE DiscretesInput SET VALUE = 1 WHERE ID = %s", (i,))
                else:
                     cursor.execute("UPDATE DiscretesInput SET VALUE = 0 WHERE ID = %s", (i,))
                i = i + 1
            self.__Database.connection.commit()
            time.sleep(1)

    def __AddProcessToWatch(self):
        self.Process    = self.ProcessEntry.get().lower() + '.exe'
        exists          = False
        processes       = GetProcesses()
        for process in processes:
            if process == self.Process:
                exists = True
                break
        if exists:
            self.MessageLabelProcess.config(text = 'Process Added')
        else:
            self.MessageLabelProcess.config(text = 'Process Not Found')
            return
        processes = open("Processes.txt", "r").read().split('\n')
        processes = processes[:len(processes) - 1]
        if '' in processes:
            processes.remove('')
        if self.Process in processes:
            return
        else:
            f = open("Processes.txt", "a")
            f.write(self.Process + '\n')
            f.close()

    def __Submit(self):
        self.IP       = ''
        self.Password = []
        if self.IPInput.get() == '':
            self.MessageLabel.config(text='Invalid IP')
            return
        IP = self.IPInput.get().split('.')
        if len(IP) != 4:
            self.MessageLabel.config(text='Invalid IP')
            return
        if not all(c.isnumeric() for c in IP):
            self.MessageLabel.config(text='Invalid IP')
            return
        if not all(0 <= int(c) <= 255 for c in IP):
            self.MessageLabel.config(text='Invalid IP')
            return
        if self.PasswordInput.get() == "":
            self.MessageLabel.config(text="Invalid Password", width='35')
            return
        if len(self.PasswordInput.get()) != 8:
            self.MessageLabel.config(text="Invalid Password", width='35')
            return
        if not self.PasswordInput.get().isnumeric():
            self.MessageLabel.config(text="Invalid Password", width='35')
            return
        self.IP = self.IPInput.get()
        self.Password.extend([IntToBytes(0, int(self.PasswordInput.get()[0:4]), 2)[0], IntToBytes(0, int(self.PasswordInput.get()[0:4]), 2)[1], IntToBytes(0, int(self.PasswordInput.get()[4:8]), 2)[0], IntToBytes(0, int(self.PasswordInput.get()[4:8]), 2)[1]])
        self.message = self.__CreateAccount(self.IP, bytes(self.Password))
        self.MessageLabel.config(text = self.message)

    def Run(self):
        self.__GUIThread.start()
        self.__ListeningThread.start()
        self.__ResourcesThread.start()
    
if __name__ == '__main__':
    ProcessesFile = os.path.isfile('Processes.txt') 
    if not ProcessesFile:
        f = open('Processes.txt', 'w+')
    Check = [False, False]
    try:
        import mysql.connector
    except:
        Check[0] = True
    try:
        import psutil
    except:
        Check[1] = True
    if Check[0] or Check[1]:
        os.system('pip install pip')
        os.system('pip install --upgrade pip')
        if Check[0]:
            os.system('pip install mysql-connector-python')
        if Check[1]:
            os.system('pip install psutil')
    ApplicationClientModbusTCP = Application()
    ApplicationClientModbusTCP.Run()