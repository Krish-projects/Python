from pyvesc.messages.base import VESCMessage

class GetValues(metaclass=VESCMessage):
    """ Gets internal sensor data
    """
    id = 4
    fields = [
            ('temp_fet', 'h', 10),
            ('temp_motor', 'h', 10),
            ('current_motor', 'i', 1000),
            ('current_in',  'i', 1000),
            ('current_d',  'i', 1000),
            ('current_q',  'i', 1000),
            ('duty_now',    'h', 10),
            ('rpm',         'i', 1),
            ('v_in',        'h', 1000),
            ('amp_hours',   'i', 1000),
            ('amp_hours_charge',   'i', 1000),
            ('watt_hours',  'i', 1000),
            ('watt_hours_charge',  'i', 1000),
            ('tachometer', 'i', 1),
            ('tachometer_abs', 'i', 1),
            ('mc_fault_code', 'i'),
            ('pid_pos','i',1),
            ('id','c'),
            ('temp_ntc1', 'h', 10),
            ('temp_ntc2', 'h', 10),
            ('temp_ntc3', 'h', 10)
            #('volt_d',  'i', 1000),
            #('volt_q',  'i', 1000)
    ]
#    fields = [
#            ('temp_mos1', 'h', 10),
#            ('temp_mos2', 'h', 10),
#            ('temp_mos3', 'h', 10),
#            ('temp_mos4', 'h', 10),
#            ('temp_mos5', 'h', 10),
#            ('temp_mos6', 'h', 10),
#            ('temp_pcb',  'h', 10),
#            ('current_motor', 'i', 100),
#            ('current_in',  'i', 100),
#            ('duty_now',    'h', 1000),
#            ('rpm',         'i', 1),
#            ('v_in',        'h', 10),
#            ('amp_hours',   'i', 10000),
#            ('amp_hours_charged', 'i', 10000),
#            ('watt_hours',  'i', 10000),
#            ('watt_hours_charged', 'i', 10000),
#            ('tachometer', 'i', 1),
#            ('tachometer_abs', 'i', 1),
#            ('mc_fault_code', 'c')
#    ]

class FwVersion(metaclass=VESCMessage):
    """ Gets firmware version
    """
    id = 0

    fields = [
            ('fw_version_major', 'c'),
            ('fw_version_minor', 'c')
    ]


class GetRotorPosition(metaclass=VESCMessage):
    """ Gets rotor position data
    
    Must be set to DISP_POS_MODE_ENCODER or DISP_POS_MODE_PID_POS (Mode 3 or 
    Mode 4). This is set by SetRotorPositionMode (id=21).
    """
    id = 21

    fields = [
            ('rotor_pos', 'i', 100000)
    ]
