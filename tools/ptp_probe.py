#!/usr/bin/env python3
"""Read-only PTP/MTP probe. Only issues GetDeviceInfo, OpenSession,
GetStorageIDs, GetStorageInfo, CloseSession, plus standard GET descriptors."""
import struct
import usb.core
import usb.util

VID, PID = 0x1f3a, 0x4ee1
EP_OUT, EP_IN = 0x01, 0x81
TIMEOUT = 4000

dev = usb.core.find(idVendor=VID, idProduct=PID)
if dev is None:
    raise SystemExit("device not found")

# MS OS string descriptor (index 0xEE): MTP devices usually answer "MSFT100"
try:
    raw = dev.ctrl_transfer(0x80, 6, 0x03EE, 0, 254, TIMEOUT)
    print("MS OS string:", bytes(raw[2:]).decode("utf-16-le", "replace"), "bytes:", bytes(raw).hex())
except Exception as e:
    print("MS OS string: error", e)

usb.util.claim_interface(dev, 0)
tid = 0


def send(op, params=()):
    global tid
    tid += 1
    length = 12 + 4 * len(params)
    pkt = struct.pack("<IHHI", length, 1, op, tid) + b"".join(struct.pack("<I", p) for p in params)
    dev.write(EP_OUT, pkt, TIMEOUT)


def recv():
    """Return (data_bytes, response_code, response_params)."""
    data = b""
    while True:
        buf = bytes(dev.read(EP_IN, 1 << 16, TIMEOUT))
        length, ctype, code, _ = struct.unpack("<IHHI", buf[:12])
        if ctype == 2:  # data container, may span several reads
            payload = buf[12:]
            while len(payload) < length - 12:
                payload += bytes(dev.read(EP_IN, 1 << 16, TIMEOUT))
            data = payload
        elif ctype == 3:
            n = (length - 12) // 4
            return data, code, struct.unpack("<%dI" % n, buf[12:12 + 4 * n])
        else:
            print("unexpected container", ctype, hex(code))


class R:
    def __init__(self, b):
        self.b, self.i = b, 0

    def u(self, fmt):
        v = struct.unpack_from("<" + fmt, self.b, self.i)[0]
        self.i += struct.calcsize(fmt)
        return v

    def s(self):
        n = self.u("B")
        if not n:
            return ""
        t = self.b[self.i:self.i + 2 * n].decode("utf-16-le", "replace").rstrip("\0")
        self.i += 2 * n
        return t

    def a(self):
        n = self.u("I")
        return [self.u("H") for _ in range(n)]


def h(lst):
    return " ".join("%04x" % x for x in lst)


try:
    send(0x1001)
    data, code, _ = recv()
    print("GetDeviceInfo response: 0x%04x, %d bytes" % (code, len(data)))
    r = R(data)
    print("StandardVersion", r.u("H"), "VendorExtID", r.u("I"), "VendorExtVer", r.u("H"))
    print("VendorExtDesc:", r.s())
    print("FunctionalMode", r.u("H"))
    print("Operations:", h(r.a()))
    print("Events:", h(r.a()))
    print("DeviceProps:", h(r.a()))
    print("CaptureFormats:", h(r.a()))
    print("PlaybackFormats:", h(r.a()))
    print("Manufacturer:", r.s())
    print("Model:", r.s())
    print("DeviceVersion:", r.s())
    print("Serial:", r.s())
except Exception as e:
    print("GetDeviceInfo failed:", repr(e))

try:
    tid = 0
    send(0x1002, (1,))
    _, code, _ = recv()
    print("OpenSession response: 0x%04x" % code)
    send(0x1004)
    data, code, _ = recv()
    print("GetStorageIDs response: 0x%04x" % code)
    r = R(data)
    ids = [r.u("I") for _ in range(r.u("I"))] if data else []
    print("Storages:", ["%08x" % i for i in ids])
    for sid in ids:
        send(0x1005, (sid,))
        data, code, _ = recv()
        r = R(data)
        st, fs, ac = r.u("H"), r.u("H"), r.u("H")
        cap, free, objs = r.u("Q"), r.u("Q"), r.u("I")
        print("  %08x type=%d fs=%d access=%d cap=%.2fGB free=%.2fGB desc=%r label=%r"
              % (sid, st, fs, ac, cap / 1e9, free / 1e9, r.s(), r.s()))
    send(0x1003)
    _, code, _ = recv()
    print("CloseSession response: 0x%04x" % code)
except Exception as e:
    print("Session phase failed:", repr(e))

usb.util.release_interface(dev, 0)
