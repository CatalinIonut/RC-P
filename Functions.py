def BytesToWord(Bytes):
    return (Bytes[0] << 8) + Bytes[1]

def IntToBytes(offset, number, dim):
    return (offset + number).to_bytes(dim, 'big')
       
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