def decode_frequency_rebanded(cmd):
    # Based on http://home.ica.net/~phoenix/wap/TRUNK88/Motorola%20Channel%20Numbers.txt
    if cmd <= 0x1B7:
        return 851012500 + 25000*cmd
    if cmd <= 0x22F:
        return 851025000 + 25000*(cmd-0x1B8)
    if cmd <= 0x2CF:
        return 865012500 + 25000*(cmd-0x230)
    if cmd <= 0x2F7:
        return 866000000 + 25000*(cmd-0x2D0)
    if cmd <= 0x32E:
        return 0 # Bogon
    if cmd <= 0x33F:
        return 867000000 + 25000*(cmd-0x32F)
    if cmd <= 0x3BD:
        return 0 # Bogon
    if cmd == 0x3BE:
        return 868975000
    if cmd <= 0x3C0:
        return 0
    if cmd <= 0x3FE:
        return 867425000 + 25000*(cmd-0x3C0)
    if cmd == 0x3FF:
        return 0

    return 0
