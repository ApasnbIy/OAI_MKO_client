from ctypes import *
import os
import oai_modbus
import json
import re
class CfgParameter:
    def __init__(self, **kwargs):
        self.serial_number = kwargs.get('serial_num', '208236A0424D')

class Device:
    """
    Device- класс устройства для общения по МКО/МПИ. Необходимо создавать по шаблону:
    метода на запись: send_to_rt(self, adr, subaddr, data, leng), возвращает ответное слово
    метода на чтение: read_from_rt(self, addr, subaddr, leng), возвращает данные с подадреса
    метода на запись команды управления: send_cntrl_command(self, addr, subaddr, leng), возвращает ответное слово !не реализовано в ПО платы

    параметр ответное слово: answer_word
    параметр командное слово: command_word

    параметр имени устройства: name
    параметр состояние устройства: state - 0-устройство подключилось,
                                           1-устройство не подключено,
                                           2-устройство не подключено к МКО ОУ
    параметр состояние устройства: bus_state -  0-неопределено,
                                                1-используется основная шина,
                                                2-используется резервная шина

    """
    def __init__(self, *args, **kwargs):
        self.name = "OAI_MKO"

        self.uniq_name = "oai_kpa_mko"
        self.bus_1, self.bus_2 = 0x02, 0x01
        self.bus_state = 0
        # объект с параметрами
        self.debug = kwargs.get('debug', False)
        self.default_cfg = self.load_cfg()
        self.serial_number = self.default_cfg["core"]["serial_num"]

        # создание объекта для общения по МодБас
        self.client = oai_modbus.OAI_Modbus(serial_num=[self.serial_number])
        self.client.debug_print_flag = True
        # параметры связи
        self.state = 1

        # constants from API.h-file возможно что тут это не нужно
        self.ALL_TMKS = 0x00FF

        self.DATA_BC_RT = 0x00
        self.DATA_BC_RT_BRCST = 0x08
        self.DATA_RT_BC = 0x01
        self.DATA_RT_RT = 0x02
        self.DATA_RT_RT_BRCST = 0x0A

        self.CTRL_C_A = 0x03
        self.CTRL_C_BRCST = 0x0B
        self.CTRL_CD_A = 0x04
        self.CTRL_CD_BRCST = 0x0C
        self.CTRL_C_AD = 0x05
        #
        self.BUS_1, self.BUS_2 = 0x2, 0x0
        #
        self.bus = self.BUS_1
        self.read_status = 0x0000
        self.answer_word = 0xFFFF
        self.command_word = 0x0000
        #
        self.register_addr = {
            "Scaler": 1349,
            "CommandWord": 1350,
            "AnswerWord": 1351,
            "Data": 1352,
        }
        #

    def save_default_cfg(self):
        try:
            os.mkdir("cfg")
        except OSError as error:
            pass
        #
        with open("cfg\\" + self.uniq_name + ".json", 'w', encoding="utf-8") as cfg_file:
            json.dump(self.default_cfg, cfg_file, sort_keys=True, indent=4, ensure_ascii=False)

    def load_cfg(self):
        try:
            with open("cfg\\" + self.uniq_name + ".json", 'r', encoding="utf-8") as cfg_file:
                loaded_cfg = json.load(cfg_file)
        except FileNotFoundError:
            loaded_cfg = self.default_cfg
        return loaded_cfg

    def init(self):
        pass
        #ничего делать не нужно
        #self.connect()
        #self.client.disconnect()

    def connect(self):
        """
               connection to the HW-module
               connection parameter can be updated
               don't use serial num
               :return: state
         """
        self.state = 1
        self.client.connect()
        #
        status = self.client.connect()
        if status == 1:
            print("status = 1")
            self.state = 0
            print("state", self.state)
        elif status == -1:
            print("status = -1")
            self.state = 1
            print("state", self.state)
        return self.state

    def disconnect(self):
        try:
            if self.client.disconnect() == 0:
                self.state = 1
            else:
                self.state = 1
        except AttributeError:
            self.state = 1
            pass
        return self.state


    def change_bus(self):
        if self.bus == self.BUS_2:
            self.bus = self.BUS_1
        else:
            self.bus = self.BUS_2
        # print(self.bus)


    def send_to_rt(self, addr, subaddr, data, leng):
        self.change_bus()
        if subaddr <= 0:
            subaddr = 1
        control_word = ((addr & 0x1F) << 11) + (0x00 << 10) + ((subaddr & 0x1F) << 5) + (leng & 0x1F)
        self.command_word = control_word
        self.answer_word = 0xFEFE
        if self.client.connect() == 1:
            self.client.write_regs(offset=self.register_addr.get("Data"), data_list=data)
            self.client.write_regs(offset=self.register_addr.get("Scaler"), data_list=[(1 | self.bus), control_word])
            temp = self.client.read_regs(target='ao', read_ranges=[
                [self.register_addr.get("AnswerWord"), self.register_addr.get("AnswerWord") + 1]])
            self.answer_word = temp[0][0]
            #temp = self.client.read_regs(target='ao', read_ranges=[[self.register_addr.get("Scaler"), self.register_addr.get("Scaler") + 1]])
            #transaction_end = temp[0][0]

            if self.answer_word == 0xFEFE:
                self.bus_state = 1 if self.bus == self.BUS_1 else 2
                self.change_bus()
                self.client.write_regs(offset=self.register_addr.get("Data"), data_list=data)
                self.client.write_regs(offset=self.register_addr.get("Scaler"), data_list=[(1 | self.bus), control_word])
                temp = self.client.read_regs(target='ao', read_ranges=[
                    [self.register_addr.get("AnswerWord"), self.register_addr.get("AnswerWord") + 1]])
                self.answer_word = temp[0][0]
                #temp = self.client.read_regs(target='ao', read_ranges=[[self.register_addr.get("Scaler"), self.register_addr.get("Scaler") + 1]])
            if (self.answer_word == 0xFEFE):
                self.state = 2
                pass
            else:
                self.state = 0
                pass
            self.client.disconnect()
        else:
            self.state = 1
            pass
        return self.answer_word

    def send_cntrl_command(self, addr, subaddr, leng):
        '''
        self.change_bus()
        control_word = ((addr & 0x1F) << 11) + (0x00 << 10) + ((subaddr & 0x1F) << 5) + (leng & 0x1F)

        if self.answer_word == 0xFEFE:
            self.state = 2
        return self.answer_word
        '''
        self.state = 2
        print('not work yet')

    def read_from_rt(self, addr, subaddr, leng):
        self.change_bus()
        if subaddr <= 0:
            subaddr = 1
        frame =[]
        control_word = ((addr & 0x1F) << 11) + (0x01 << 10) + ((subaddr & 0x1F) << 5) + (leng & 0x1F)
        self.command_word = control_word
        if self.client.connect() == 1:
            self.client.write_regs(offset=self.register_addr.get("Scaler"), data_list=[1 | self.bus, control_word])
            temp = self.client.read_regs(target='ao', read_ranges=[[self.register_addr.get("Data"), self.register_addr.get("Data")+leng]])
            frame = temp[0]
            temp = self.client.read_regs(target='ao', read_ranges=[[self.register_addr.get("AnswerWord"), self.register_addr.get("AnswerWord")+1]])
            self.answer_word = temp[0][0]
            #temp = self.client.read_regs(target='ao', read_ranges=[[self.register_addr.get("Scaler"), self.register_addr.get("Scaler")+1]])

            if self.answer_word == 0xFEFE:
                self.bus_state = 1 if self.bus == self.BUS_1 else 2
                self.change_bus()
                self.client.write_regs(offset=self.register_addr.get("Scaler"), data_list=[1 | self.bus, control_word])
                temp = self.client.read_regs(target='ao', read_ranges=[
                    [self.register_addr.get("Data"), self.register_addr.get("Data") + leng]])
                frame = temp[0]
                temp = self.client.read_regs(target='ao', read_ranges=[
                    [self.register_addr.get("AnswerWord"), self.register_addr.get("AnswerWord") + 1]])
                self.answer_word = temp[0][0]
                #temp = self.client.read_regs(target='ao', read_ranges=[[self.register_addr.get("Scaler"), self.register_addr.get("Scaler") + 1]])

            if self.answer_word == 0xFEFE:
                self.state = 2
                pass
            else:
                self.state = 0
                pass
            self.client.disconnect()
        else:
            self.state = 1
            pass



        return frame

    def print_base(self):
        print_str = ""
        for i in range(35):
            #print_str += "%04X " % self.ta1_lib.bcgetw(i)
            pass
        print(print_str)
        pass


class PollingProgram:
    """
        класс для разбора подпрограмм для создания циклограмм
        циклограмма согласно данному шаблону
        ["Name", [[Address, Subaddress, Wr/R, [Data], Data leng, Start time, Finish time, Interval, Delay], [...], [...]]]
           |          |          |        |      |         |          |           |          |         |
           |          |          |        |      |         |          |           |          |         -- Задержка отправки
           |          |          |        |      |         |          |           |          --- Интервал отправки
           |          |          |        |      |         |          |           - Время остановки посылок
           |          |          |        |      |         |          --- Время старта отправки от запуска программы
           |          |          |        |      |         --- Длина данных для приема/отправки
           |          |          |        |      ------------- Данные для отправки (при приеме не имеет значения)
           |          |          |        -------------------- Отправка - "0", Прием - "1"
           |          |          ----------------------------- Подадрес
           |          ---------------------------------------- Адрес ОУ
           --------------------------------------------------- Имя циклограммы
    """
    def __init__(self, program=None):
        program_def = ["None", [0, 0, 0, [0], 0, 0, 0, 0.1, 0]]
        self.program = program if program else program_def
        self.name = self.program[0]
        self.cycle = []
        self.parcer()

    def parcer(self):
        for i in range(len(self.program[1])):
            start_time = self.program[1][i][5]
            stop_time = self.program[1][i][6]
            interval = self.program[1][i][7]
            delay = self.program[1][i][8]
            try:
                tr_number = int((stop_time - start_time)//interval)
            except ZeroDivisionError:
                tr_number = 1
            for j in range(tr_number):
                time = start_time + j*interval + delay
                addr = self.program[1][i][0]
                subaddr = self.program[1][i][1]
                direct = self.program[1][i][2]
                data = self.program[1][i][3]
                leng = self.program[1][i][4]
                data_set = [time, addr, subaddr, direct, data, leng]
                self.cycle.append(data_set)
        self.cycle.sort()
        pass


if __name__ == '__main__':
    OAI_MKO = Device()
    addr = 19
    subaddr = 30

    #OAI_MKO.disconnect()
    #state = OAI_MKO.connect()
    data = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]
    leng = 6
    print(OAI_MKO.send_to_rt(addr, subaddr, data, leng))
    leng = 32
    data = OAI_MKO.read_from_rt(addr, subaddr, leng)
    print(data)

    '''
    #frame = OAI_MKO.read_from_rt(addr,subaddr,len)
    #frame_str = " ".join(["%04X" % var for var in frame])
    #print("aw-%04X, cw-%04X, data-%s" % (OAI_MKO.answer_word, OAI_MKO.command_word, frame_str))
    '''