# sigrok
## np2srzip
Save numpy array as srzip file.

### [sigrok input output formats](https://sigrok.org/wiki/Input_output_formats)
| Format          | Input Supported | Output Supported | Description |
|-----------------|-----------------|------------------|-------------|
| Analog          | —               | Yes              | Text output of analog data and types. |
| ASCII           | —               | Yes              | ASCII art. |
| Binary          | Yes             | Yes              | Raw binary data output without any metadata attached. |
| Bits            | —               | Yes              | 0/1 digits. |
| ChronoVu LA8    | Yes             | Yes              | ChronoVu LA8 software file format (usually with .kdt file extension). |
| CSV             | Yes             | Yes              | Comma-separated values (also usable for generating data and config files for gnuplot). |
| hex             | —               | Yes              | Hexadecimal digits. |
| Intronix Logicport LA1034 | Yes | — | Intronix Logicport LA1034 *.lpf files. |
| ols             | —               | Yes              | The file format used by the "Alternative" Java client for the Openbench Logic Sniffer. |
| protocoldata    | Yes             | —                | Re-creates logic trace waveforms from a sequence of data values and optional control instructions. |
| saleae          | Yes             | —                | Files exported by the Saleae Logic application. |
| srzip           | Yes             | Yes              | The current (v2) sigrok session file format (*.sr). |
| STF             | Yes             | —                | "Sigma Test File". Native format of the Asix Sigma/Omega vendor software. |
| VCD             | Yes             | Yes              | The Value Change Dump format (can also be visualized in gtkwave, for instance). |
| WAV             | Yes             | Yes              | The waveform audio (WAV) file format. |
| Raw analog      | Yes             | —                | Analog signals without header (configurable sample size, format, and endianness). |
| Lauterbach Trace32 | Yes       | —                | The Lauterbach Trace32 logic analyzer data file format. |
| WaveDrom        | —               | Yes              | Digital timing diagrams in JSON syntax |


### refs
- [sigrok/v2 file format](https://sigrok.org/wiki/File_format:Sigrok/v2)
- [dsview/srzip.c](https://github.com/DreamSourceLab/DSView/blob/master/libsigrok4DSL/output/srzip.c)
- [wavebin](https://github.com/konosubakonoakua/wavebin)
- [siglent-bin2sr](https://github.com/giuliof/siglent-bin2sr)

### test
#### generate multiple test cases
```bash
python -m np2srzip.test.tb_np2srzip
pulseview test_case3.sr
```

#### convert to VCD file
Analog data not working!!!
```bash
sigrok-cli -i test_case3.sr -O vcd -o test_case3.vcd
gtkwave test_case3.vcd
```

## txt2sr
convert txt data file to srzip with tk gui.

```bash
cd sigrok
python -m txt2sr.txt2sr
```

![txt2sr](./txt2sr/txt2sr.png)
![pulseview](./txt2sr/txt2sr_pulseview.png)
