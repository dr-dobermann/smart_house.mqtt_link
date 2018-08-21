"""
Module provides functionality for mqtt links processing

(c) Dr. Dobermann, 2018.
"""

from umqtt.robust import MQTTClient
from machine import Pin
import utime

import mqtt_link_consts as mlc

# Constants
#------------------------------------------------------------------------------
CHECK_TIMEOUT     = 1 * 1000   # milliseconds
KEEP_ALIVE_TIMOUT = 300 * 1000 # milliseconds

# last keep alive reply
last_kar = 0
kat = KEEP_ALIVE_TIMOUT


# Gloabal variables
#------------------------------------------------------------------------------
# last mqtt message check time
check_time = utime.ticks_ms()

# mosfet and switch string statuses
on_off_str = {
    mlc.ON: b"on",
    mlc.OFF: b"off"
    }

# link on mqtt links dictionary
ml = dict()

# mqtt client name
cname = b""

# mqtt client object
mqtt_cli = None

# list of system mqtt verbs and their processors
sys_verbs = None

# list of processors and vers allowed for every tool type linked to mqtt topic
# it organized as a dictionary with key as tool type from mqtt_links
# first item is tool processing routine
# second item is a list of allowed verbs
# third item is an init procedure for the tool type
tool_verbs = {
    b"MOSFET"    :[None, [b"?", b"on", b"off"], None],
    b"SWITCH"    :[None, [b"?", b"timeout_get", b"timeout_set"], None],
    b"SENSOR_I2C":[None, [b"?", b"timeout_get", b"timeout_set"], None],
    b"BUTTON"    :[None, [], None]
}

# Functions
#------------------------------------------------------------------------------
def cb(topic, msg):
    """
    MQTT call back processor
    """

    global ml
    global tool_verbs
    
    print("==> Got [", msg, "] from topic [", topic, "]")

    if topic in ml:
        if ml[topic][0] not in tool_verbs:
            publish_status(b"ERROR: Invalid tool type " + ml[topic][0] + b" linked to topic : " + topic)
            return

        # check if the message is equal to any verb in a tool type and if it so, process the message
        found = False
        for v in tool_verbs[ml[topic][0]][1]:
            if msg.startswith(v):
                found = True
                break
        if not found:
            publish_status(b"ERROR: Unregistered verb:" + msg, topic)
        else:
            tool_verbs[ml[topic][0]][0](topic, msg)

    elif topic == cname:
        key = None
        for v in sys_verbs.keys():
            if msg.startswith(v):
                key = v
                break
        if key == None:
            publish_status(b"ERROR: Invalid system verb: " + msg)
            return
        sys_verbs[key](msg)

    else: # despite it's impossible that controller gets topic it isn't subscribed for, I left this here
        publish_status(b"ERROR: Unregistered topic: " + topic)



def init_controller(cli_name, mqtt_links):
    """
    Prepares controller for work starting
    initializes mqtt_links
    """
    global ml
    global cname
    global mqtt_cli
    global tool_verbs

    ml = mqtt_links
    cname = cli_name

    groups = dict()

    for t, ma in ml.items():
        if ma[0] not in tool_verbs:
            print("FATAL: Invalid tool type:", ma[0], "for link", t)
            return None

        else: # run initialization routine for the tool type
            if tool_verbs[ma[0]][2](ma) != True:
                print("FATAL: Could not initialize tool type [", ma[0], "] for link [", t, "!!!")
                return None

            # check mosfet groups
            if ma[0] == b"MOSFET":
                if ma[1][3] != mlc.NO_GROUP:
                    if ma[1][3] not in groups:
                        groups[ma[1][3]] = [mlc.NO_SEQ, []] # first item is a sequence flag for a group
                    groups[ma[1][3]][1].append(ma[1][0]) # group consists of pin numbers of mosfets
                    ma[2].insert(3, groups[ma[1][3]])   # group info holds in 4th item of the run-time objects list
                    if ma[1][3] == mlc.SEQ:
                        groups[ma[1][3]][0] = mlc.SEQ
                        # sequental group has an extra item in a group list which indicates next mosfet to power on
                        if len(groups[ma[1][3]]) == 2:
                            # add next mosfet index into group info
                            # it should be the first item in a group list
                            groups[ma[1][3]].append(groups[ma[1][3]][1][0])
                else:
                    # if mosfet isn't in any group, add an empy group to its run-time
                    ma[2].insert(3, [mlc.NO_SEQ, []])

    import mqtt_cfg
    
    c = MQTTClient(cname, mqtt_cfg.mqtt_srv_name)
    print("Trying to connect to", mqtt_cfg.mqtt_srv_name)
    c.DEBUG = True
    c.connect(clean_session = False)
    print("Connected")
    c.set_callback(cb)

    # subscribe for mqtt links
    for mak in ml.keys():
        c.subscribe(mak)
        print("Subscribed for", mak)

    # subscribe for system mqtt requests
    c.subscribe(cname)
    print("Subscribed for", cname)

    mqtt_cli = c

    publish_status(b"READY")

    return c



def close_controller():
    """
    Closes controller and shut down mqtt connection
    """

    mqtt_cli.disconnect()



def run():
    """
    Executes application main cycle step
    """
    global check_time
    global tool_verbs
    global last_kar
    global kat

    if utime.ticks_ms() > check_time:
        # check for mqtt messages
        mqtt_cli.check_msg()
        # check mqtt links states
        for t, l in ml.items():
            tool_verbs[l[0]][0](t, b"")
        check_time = utime.ticks_ms() + CHECK_TIMEOUT

    if utime.ticks_ms() - last_kar > kat:
        publish_status(b"STEADY" + b":{}".format(int(utime.ticks_ms()/1000)))
        last_kar = utime.ticks_ms()

    return True



def reset(msg):
    """
    Resets the board
    """
    publish_status(b"GOING RESET")
    from machine import reset
    reset()



def get_sys_info(msg):
    """
    Return the system information
    Name:uptime in seconds:keep alive timout in secondes
    """
    global cname
    global kat

    publish_status(cname + b":{}:".format(int(utime.ticks_ms()/1000)) + b"{}".format(int(kat/1000)))



def get_mqtt_links(msg):
    """
    Returns the mqtt links registered on the device
    
    topic:tool_type:state
    """
    global ml

    mls = b""
    for t, l in ml.items():
        if l[0] == b"MOSFET":
            mls += t + ":" + l[0] + ":" + on_off_str[l[2][1]] + "\n"
        elif l[0] == b"SENSOR_I2C":
            mls += t + ":" + l[0] + ":" + l[1][1] + ":" + l[1][2] + "\n"
        else:
            mls += t + ":" + l[0] + "\n"

    publish_status(mls)



def set_keep_alive_timeout(msg):
    """
    Sets new keep alive reply timout
    """
    global kat

    try:
        kat = int(msg.split(b':')[1], 10)
        publish_status(b"new_kat:" + b"{}".format(kat))
        kat *= 1000
    except Exception as e:
        publish_status(b"ERROR: couldn't set net KAT due to {}".format(e))



def do_mosfet(topic, verb = b""):
    """
    Checks the mosfet state and reacts on given verbs

    If verb is empty it just checks current state and if it's on,
    checks the timeout, turn it off and send response about
    """
    
    global ml

    mos = ml[topic]
    publish = False
    update = False

    if verb == b"":
        if mos[2][0].value() == mlc.ON and (mos[1][2] != -1 and utime.ticks_ms() - mos[2][2] > mos[2][3]*1000):
            update = True
            publish = True

    elif verb == b"?":
        publish = True

    elif verb.startswith(b"on"):
        if verb.startswith(b"on:"):
            try:
                tout = int(verb.split(':')[1], 10)
                # Check current mosfet's state and working time
                # calculate working time limit according to the current working time 
                if mos[2][0].value() == mlc.ON and mos[1][2] != -1:
                    limit = mos[1][2] - int((utime.tick_ms() - mos[2][2])/1000)
                else:
                    limit = -1
                if tout <= 0:
                    tout = -1
                # set new timeout according to the current time limit
                if limit != -1 and tout != -1 and limit < tout:
                    mos[2][3] = limit
                else:
                    mos[2][3] = tout

            except Exception as e:
                publish_status(b"ERROR: Invalid timeout value in" + verb + b" fired exception {}".format(e), topic)

        if mos[2][1] == mlc.OFF:
            update = True
        publish = True

    elif verb == b"off":
        if mos[2][1] == mlc.ON:
            update = True
        publish = True

    else:
        publish_status(b"ERROR: Invalid verb [" + verb + b"] in topic [" + topic + b"]")

    if publish:
        if update:
            if mos[2][0].value() == mlc.ON:
                mos[2][0].off()
                # update mosfet group if need be
                if len(mos[2][3][1]) > 1:
                    if mos[2][3][0] == mlc.SEQ:
                        # get current mosfet index in a group and increase it
                        ii = mos[2][3][1].index(mos[2][3][2])
                        ii += 1
                        if ii > len(mos[2][3][1]) - 1:
                            ii = 0
                        mos[2][3][2] = mos[2][3][1][ii]
            else:
                # if the mosfet is in a group, check possibility to turn it on
                if len(mos[2][3][1]) > 1: 
                    if mos[2][3][0] == mlc.SEQ:
                        # if it's a sequental group of mosfets, the mosfet pin should be equal 
                        # to the next mosfet in a group id to be powered on
                        if mos[1][0] == mos[2][3][2]:
                            mos[2][0].on()
                    else:
                        # check if every group mosfet is off then turn it on
                        found = False
                        for l in ml.values():
                            if l[0] == b"MOSFET":
                                if l[1][0] != mos[1][0] and l[1][0] in mos[2][3][1] and l[2][0].value() == mlc.ON:
                                    found = True
                                    break
                        if not found:
                            mos[2][0].on()
                        else:
                            if verb == b"on":
                                publish_status(b"WARNING: Could not start " + topic + b" due to group [{}] conflict".format(mos[1][3]))
                else:
                    mos[2][0].on()

            mos[2][1] = mos[2][0].value()
            mos[2][2] = utime.ticks_ms()
        if mos[2][1] == mlc.ON:
            reply = on_off_str[mos[2][1]] + b" {}/{}".format(int((utime.ticks_ms() - mos[2][2])/1000), mos[2][3])
        else:
            reply = on_off_str[mos[2][1]] + b" {}".format(int((utime.ticks_ms() - mos[2][2])/1000))
        if verb == b"?":
            reply += b":{}".format(mos[1][2])
        publish_status(reply, topic)



def do_switch(topic, verb = b""):
    """
    Checks the switch state on timeout and reacts on given verbs

    If verb is empty it just checks current state. 
    if timeout is reached or the state is changed then publish the state on mqtt server
    """

    global ml

    sw = ml[topic]
    publish = False
    
    newVal = sw[2][0].value()
    if verb == b"":
        if  newVal != sw[2][1] or (sw[1][1] != -1 and utime.ticks_ms() - sw[2][2] > sw[1][1] * 1000):
            publish = True
            
    elif verb == b"?":
        publish = True

    elif verb == b"timeout_get":
        publish_status(b"{}".format(sw[1][1]), topic)

    elif verb.startswith("timeout_set:"):
        try:
            sw[1][1] = int(verb.split(':')[1], 10)
            publish_status(b"{}".format(sw[1][1]), topic)
            sw[2][2] = utime.ticks_ms()

        except Exception as e:
            publish_status(b"ERROR: Invalid timeout set command " + verb + b" fired exception {}".format(e), topic)

    else:
        publish_status(b"ERROR: Invalid verb [" + verb + b"] in topic [" + topic + b"]")

    if publish:
        if newVal != sw[2][1]: # update switch values if needed before publishing them
            sw[2][1] = newVal
            sw[2][2] = utime.ticks_ms()
        publish_status(on_off_str[sw[2][1]] + b" {}".format(int((utime.ticks_ms() - sw[2][2])/1000)), topic)



def do_sensor_i2c(topic, verb = b""):
    """
    Checks sensor value as needed and process verbs

    If verb is empty it just checks current state. 
    if timeout is reached then updates value and publish it on mqtt server
    """

    global ml

    sens = ml[topic]
    publish = False

    if verb == b"":
        if sens[1][2] != -1 and utime.ticks_ms() - sens[2][2] > sens[1][2] * 1000:
            publish = True

    elif verb == b"?":
        publish = True

    elif verb == b"timeout_get":
        publish_status(b"{}".format(sens[1][2]), topic)

    elif verb.startswith("timeout_set:"):
        try:
            sens[1][1] = int(verb.split(':')[1], 10)
            publish_status(b"{}".format(sens[1][2]), topic)
            sens[2][2] = utime.ticks_ms()

        except Exception as e:
            publish_status(b"ERROR: Invalid timeout set command " + verb + b" fired exception {}".format(e), topic)

    else:
        publish_status(b"ERROR: Invalid verb [" + verb + b"] in topic [" + topic + b"]")

    if publish:
        sens[2][1] = sens[2][0].get_value(True)
        sens[2][2] = utime.ticks_ms()
        publish_status(sens[2][1], topic)



def do_button(topic, verb = b""):
    print("do_button isn't implemented yet")



def init_mosfet(mos):
    """
    Init single mosfet and create necessary run-time objects and data
    """
    p = Pin(mos[1][0], Pin.OUT)
    if mos[1][1] == mlc.ON:
        p.on()
    else:
        p.off()
    # Pin should be the first item in the run-time objects
    mos[2].insert(0, p)         
    # Mosfet current state should be the second item
    mos[2].insert(1, p.value())
    # Mosfet status change time should be the third item
    mos[2].insert(2, utime.ticks_ms())
    # Current mosfet timeout is placed as forth item
    mos[2].insert(3, mos[1][2])


    return True



def init_switch(sw):
    """
    Init single switch and create necessary run-time objects and data
    """
    p = Pin(sw[1][0], Pin.IN)
    # Pin should be the first item in the run-time objects
    sw[2].insert(0, p)
    # Current state should be second item
    sw[2].insert(1, p.value())
    # Checked time should be third item
    sw[2].insert(2, utime.ticks_ms())

    return True



def init_sensor_i2c(sI2c):
    """
    Init single I2C sensor and create necessary run-time objects and data
    """
    from sensors.sens_cont import SensorController
    from sensors.i2c import get_sensor
    s = get_sensor(sI2c[1][0][0], sI2c[1][0][1], sI2c[1][1])
    if s == None:
        print("FATAL: Couldn't init sensor", sI2c[1][1], "on I2C bus", sI2c[1][0])
        return False

    if s.status != SensorController.OK:
        print("FATAL: Created sensor isn't OK")
        return False

    sI2c[2].insert(0, s) # first item is sensor
    sI2c[2].insert(1, b"") # second item is the current value of the sensor
    sI2c[2].insert(2, utime.ticks_ms()) # third item is the last update time

    return True



def init_button(butt):
    """
    Init single button and create necessary run-time objects and data
    """
    return True



def publish_status(msg, topic = None):
    """
    Publish status on the mqtt server
    """
    global cname

    if topic == None:
        topic = cname
    t = topic + b"/status"
    print("<== Message [", msg, "] published on topic", t)
    mqtt_cli.publish(t, msg)




# Module initialization
#------------------------------------------------------------------------------
if __name__ != "__main__":
    sys_verbs = dict()
    sys_verbs[b"?"] = get_sys_info
    sys_verbs[b"reset"] = reset
    sys_verbs[b"get_links"] = get_mqtt_links
    sys_verbs[b"set_kat"] = set_keep_alive_timeout

    tool_verbs[b"MOSFET"][0] = do_mosfet
    tool_verbs[b"MOSFET"][2] = init_mosfet
    tool_verbs[b"SWITCH"][0] = do_switch
    tool_verbs[b"SWITCH"][2] = init_switch
    tool_verbs[b"SENSOR_I2C"][0] = do_sensor_i2c
    tool_verbs[b"SENSOR_I2C"][2] = init_sensor_i2c
    tool_verbs[b"BUTTON"][0] = do_button
    tool_verbs[b"BUTTON"][2] = init_button
