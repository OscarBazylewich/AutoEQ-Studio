"""A stand-in Equalizer APO config folder for the tests (the real one is never touched): the self-test's two EQ files
and config.txt, byte for byte (selftest.py lines 28-31), and fake_apo(top), which makes <top>\\apo\\config with them.

EARPODS  an EQ file: a pre-amp and three filters, one of them off (CRLF, as Notepad saves)
SAMSON   an EQ file saved as Notepad's "Unicode" (UTF-16) with a decimal comma
CONFIG   config.txt (UTF-8 with a BOM, CRLF): Samson.txt's Include turned off, EarPods.txt's on
"""
import os

EARPODS = b"Preamp: -26.7 dB\r\nFilter 1: ON LSC Fc 105 Hz Gain 9.0 dB Q 0.70\r\nFilter 2: ON PK Fc 2000 Hz Gain -2 dB Q 1\r\n" \
          b"Filter 3: OFF PK Fc 5000 Hz Gain 1 dB Q 2\r\n"
SAMSON = "Preamp: -3,3 dB\nFilter: ON PK Fc 60 Hz Gain 3 dB Q 0.7\n".encode("utf-16")  # (Notepad's "Unicode", a comma)
CONFIG = "# Include: Samson.txt\r\nInclude: EarPods.txt\r\n".encode("utf-8-sig")


def fake_apo(top) -> str:
    """<top>\\apo\\config with config.txt, EarPods.txt and Samson.txt (selftest.py's fake_apo, line 34): the folder."""
    conf = os.path.join(top, "apo", "config")
    os.makedirs(conf)
    for name, raw in (("config.txt", CONFIG), ("EarPods.txt", EARPODS), ("Samson.txt", SAMSON)):
        with open(os.path.join(conf, name), "wb") as fh:
            fh.write(raw)
    return conf
