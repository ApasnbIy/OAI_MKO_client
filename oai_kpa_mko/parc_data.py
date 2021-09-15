
# модуль собирающий в себе стандартизованные функции разбора данных
# Стандарт:
# параметры:
#     frame - в виде листа с данными
# возвращает:
#     table_list - список подсписков (подсписок - ["Имя", "Значение"])

import threading

# замок для мультипоточного запроса разбора данных
data_lock = threading.Lock()


def val_from(frame, param, param1, byteorder):
    pass


def frame_parcer(frame):
    try:
        with data_lock:
            data = []
            #
            while len(frame) < 3:
                frame.append(0xFEFE)
                pass
            #
            if frame[0] == 0x0FF1 or frame[0] == 0xF10F:  # проверка на метку кадра
                b_order = 'big' if frame[0] == 0x0FF1 else 'little'
                if 0x4461 == val_from(frame, 2, 2, byteorder=b_order):  # БДД_МК системный кадр
                    #
                    data.append(["Метка кадра", "0x%04X" % val_from(frame, 0*2, 2, byteorder=b_order)])
                    data.append(["Определитель", "0x%04X" % val_from(frame, 1*2, 2, byteorder=b_order)])
                    data.append(["Ввремя, с", "%d" % val_from(frame, 3 * 2, 4, byteorder=b_order)])
                    #
                    pass
                elif 0x4462 == val_from(frame, 1*2, 2, byteorder=b_order, signed=False):  # БДД_МК кадр с подробными данными
                    data.append(["Метка кадра", "0x%04X" % val_from(frame, 0 * 2, 2, byteorder=b_order)])
                    data.append(["Определитель", "0x%04X" % val_from(frame, 1 * 2, 2, byteorder=b_order)])
                    data.append(["Ввремя, с", "%d" % val_from(frame, 3 * 2, 4, byteorder=b_order)])
                    # oai dd 1 and 2
                    for i in range(2):
                        data.append(["Режим", "0x%02X" % val_from(frame, 2 * 5 + i*16, 1, byteorder=b_order)])
                        data.append(["Статус", "0x%02X" % val_from(frame, 2 * 5 + 1 + i*16, 1, byteorder=b_order)])
                        data.append(["P дд, мм рт.ст.", "%.2E" % val_from(frame, 2 * 6 + i*16, 2, byteorder=b_order)])
                        data.append(["T, °C.", "%.2f" % (val_from(frame, 2 * 7 + i*16, 2, byteorder=b_order)/256)])
                        data.append(["U ЦАП, В", "%.3f" % (val_from(frame, 2 * 8 + i*16, 2, byteorder=b_order) / 256)])
                        data.append(["U дд, В", "%.3f" % (val_from(frame, 2 * 9 + i*16, 2, byteorder=b_order) / 256)])
                        data.append(["I дд, мА", "%.3f" % (val_from(frame, 2 * 10 + i*16, 2, byteorder=b_order) / 256)])
                        data.append(["R дд, Ом", "%.3f" % (val_from(frame, 2 * 11 + i*16, 2, byteorder=b_order) / 256)])
                    #
                    pass
                else:
                    data.append(["Неизвестный определитель", "0"])
            else:
                data.append(["Данные не распознаны", "0"])
            return data
    except Exception as error:
        print(error)
        return []


def val_from(frame, offset, length, byteorder="little", signed=False, debug=False):
    """
    обертка для функции сбора переменной из оффсета и длины, пишется короче и по умолчанию значения самые используемые
    :param frame: лист с данными кадра
    :param offset: оффсет переменной в байтах от начала кадра
    :param length: длина переменной в байтах
    :param byteorder: порядок следования байт в срезе ('little', 'big')
    :param signed: знаковая или не знаковая переменная (True, False)
    :return: итоговое значение переменной
    """
    # делаем из списка слов список байт
    byte_list = []
    for i in range(64):
        byte_list.append((frame[i//2] >> (8 * ((i+1) % 2))) & 0xFF)
    bytes_frame = bytearray(byte_list)
    ret_val = int.from_bytes(bytes_frame[offset + 0:offset + length], byteorder=byteorder, signed=signed)
    if debug:
        print(bytes_frame)
        print(bytes_frame[offset + 0:offset + length],
              " %04X" % int.from_bytes(bytes_frame[offset + 0:offset + length], byteorder=byteorder, signed=signed))
    return ret_val


def _int_to_time(sec):
    return [sec//3600, (sec//60) % 60, sec % 60]


def dep_field(data, a=0.1, b=0):
    scale = data >> 15
    mantissa = (data & 0x3FF)
    if (mantissa & 0x200) == 0:
        mantissa = - mantissa
    else:
        mantissa = (((~mantissa) + 1) & 0x3FF)
    degree = (data >> 10) & 0x1F
    sign = (data >> 9) & 1
    field = (mantissa * (2 ** (23 - degree)) * (10 ** (-scale)) / (2 ** 18)) * a + b
    return (-1**sign) * field


def dep_freq(data):
        if data > 127:
            data -= 256
        freq = 5e6 / (33333 + (data * (2 ** 7)))
        return freq

