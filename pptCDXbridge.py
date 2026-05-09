# Copyright (c) 2021 mmaskeri
from AppKit import NSPasteboard, NSRange, NSData, NSMakeRange, NSNotFound
import logging

# module logger
logger = logging.getLogger("pptCDXbridge")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)


def find_cdx_in_bytes(data_bytes, search_bytes=b'VjCD0100'):
    """Pure-Python search for the CDX header inside a bytes object.

    Returns the start index if found, otherwise None.
    """
    if not data_bytes or not search_bytes:
        return None
    idx = data_bytes.find(search_bytes)
    return idx if idx != -1 else None
### Binary header for CDX blob, used as search term
sterm = NSData.alloc().initWithBytes_length_('VjCD0100'.encode('utf-8'), 8)


def main():
    pb = NSPasteboard.generalPasteboard()
    pbItems = pb.pasteboardItems()
    types = pbItems[0].types()
    count = types.count()

    datastart_loc = NSNotFound
    for i in range(0, count):
        ret = pb.dataForType_(types[i])
        # skip empty or missing data to avoid creating negative/oversized NSRange
        if ret is None:
            logger.debug("pasteboard item %d: no data, skipping", i)
            continue
        length = ret.length()
        if length == 0:
            logger.debug("pasteboard item %d: empty data, skipping", i)
            continue

        maxrng = NSMakeRange(0, length - 1)
        # try native NSData search first; fallback to pure-Python bytes search on error
        try:
            ds = ret.rangeOfData_options_range_(sterm, 0, maxrng)
            datastart_loc = ds.location
        except Exception as e:
            logger.warning("NSData.rangeOfData_options_range_ failed for item %d: %s; falling back to bytes search", i, e)
            # attempt to convert NSData to Python bytes and search
            pybytes = None
            try:
                pybytes = bytes(ret)
            except Exception:
                try:
                    bobj = ret.bytes()
                    pybytes = bobj.tobytes() if hasattr(bobj, 'tobytes') else bytes(bobj)
                except Exception:
                    pybytes = None

            if pybytes is not None:
                idx = find_cdx_in_bytes(pybytes, b'VjCD0100')
                datastart_loc = idx if idx is not None else NSNotFound
            else:
                logger.debug("pasteboard item %d: could not obtain bytes from NSData", i)
                datastart_loc = NSNotFound

        # check to see if search term is successful
        if datastart_loc != NSNotFound:
            logger.info("Found CDX header in pasteboard item %d at offset %s", i, datastart_loc)
            break

    if datastart_loc == NSNotFound:
        logger.info("CDX header not found in any pasteboard items; exiting")
        return

    # range of valid binary CDX data in pasteboard item
    datarng = NSMakeRange(datastart_loc, ret.length() - datastart_loc)

    # pull subdata range from main pasteboard item
    outdata = ret.subdataWithRange_(datarng)

    # binary CDX data obtained; putting back on clipboard in format recognizable to ChemDraw
    perkinelmerType = u'com.perkinelmer.chemdraw.cdx-clipboard'
    pb.clearContents()
    pb.setData_forType_(outdata, perkinelmerType)


if __name__ == '__main__':
    main()
