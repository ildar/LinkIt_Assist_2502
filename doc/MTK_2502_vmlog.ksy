meta:
  id: vmlog
  file-extension: log
  endian: be
  license: GPL
  title: MTK vm_log() output (from monitor USB stream)

seq:
  - id: records
    type: record
    repeat: eos

types:
  record:
    doc: record format taken from mon.py
    seq:
      - id: rectype
        type: u1
      - id: record_body
        type:
          switch-on: rectype
          cases:
            0x55: record55body
            0xa5: recorda5body
            _: empty # skip if rectype is garbage
  record55body:
    seq:
      - id: magic55_2ndpart
        contents:
          - 0x00
      - id: length
        type: u1
      - id: packet_id
        type: u1
      - id: data
        type: str
        encoding: ascii
        size: length
      - id: checksum
        type: u1
  recorda5body:
    seq:
      - id: length
        type: u1
      - id: data
        type: str
        encoding: ascii
        size: length
      - id: frame_no
        type: u1
      - id: checksum
        type: u1
  empty: {}
