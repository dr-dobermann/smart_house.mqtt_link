# Smart House MQTT Tools Node

Node run over microcontroller and manages one or more tools linked to the MQTT topic.

## MQTT Links

## **Due to the library is too big for an on-time compilling, compile it first with mpy-cross**


The logic of controller's activity described in **mqtt_links** dictionary. It has structure as followed:
* The key is the mqtt topic name. 
* The value link description presented as a list. It has three elements:
   1. Item 0 of the list is the **tool type** linked to the mqtt topic.
   2. Item 1 holds **tool type parameters** necessary for the mqtt link description
   3. Item 2 keeps **run-time objects and information** created to support link functionality (Pin, current timeouts, statuses, etc). This list will be created after program started.


### Tool types

**Tool types** could be any of listed below:  

|Type         | Description                                                           |
|-------------|-----------------------------------------------------------------------|
|MOSFET       | Controls power load on the given pin                                  |
|SENSOR_I2C   | Controls sensor connected over I2C bus                                |
|SWITCH       | Controls the switch or digital sensor connected to the given pin      |
|BUTTON       | Controls the button connected to the given pin                        |

    
### Tool type parameters

**Tool type parameters** is a list. Every list item depends on used **tool type**.

|Tool Type  | Param ID | Description
|-----------|----------|------------------------------------------------------
|MOSFET     | 0        | Digital pin id
|           | 1        | Initial state. `[1 or ON, 0 or OFF]`
|           | 2        | Maximum time to keep power on the pin in seconds. **-1** means forever
|           | 3        | Group ID. The mosfet in the same group couldn't start simultaneously. It's possible to start only one at a time.<br/>**-1** means the mosfet isn't in any group `mqtt_link.NO_GROUP`
|           | 4        | Sequental powering on of a grouped mosfets. If the mosfet is in a group, grouped mosfet could start sequentally if this item is True. If this item if False, sequence ignored. This parameter ignored completely if the mosfet isn't included in any group. `mqtt_link.SEQ | mqtt_link.NO_SEQ`<br/><br/>**If any of a group member sets a sequential powering flag, all group will be sequented**
|SENSOR_I2C | 0        | Couple to select (sda, scl) pins for I2C bus
|           | 1        | Sensor name
|           | 2        | Period for sensor updating
|SWITCH     | 0        | Digital pin id
|           | 1        | Timeout to check the switch. **-1** means no timeout and check repeatedely in main cycle.<br/>If the switch state has changed since the last check, new message will be publish on the mqtt server
|BUTTON     | 0        | Digital pin id
|           | 1        | b"UP" or b"DOWN" for pulling up or down connected button


So finally the structure of the actions' list might be formed as followed
```python
    mqtt_actions = {
        b"{dev_name}/mqtt_topic1": ["MOSFET", [1, 180, -1, False], []] # mosfet is active for no more than 180 seconds
        b"{dev_name}/mqtt_topic2": ["SWITCH", [2, -1], []]  # check switch in the main cycle with no strict timeout 
                                                 # and send status change events

        b"{dev_name}/mqtt_topic3": ["SENSOR_I2C", [(sda_pin, scl_pin), "SENSOR_NAME", 60], []] # update sensor every 60 seconds
        }

```


### Tool type verbs


Every tool type could execute its own list of verbs from mqtt message. In the next table tool type verbs listed for every tool type.

|Tool Type | Verb                           | Description                                                                     |
|----------|--------------------------------|---------------------------------------------------------------------------------|
|MOSFET    | b"?"                           | Get current status.<br/>Returned message depends on a current mosfet state:<br/> - if it's on, the reply message would be as this *b"on {time_since}/{timeout}:{max_load_time}"* {time since} is time since last status change, {timeout} shows the time the mosfet should be work for, {max_load_time} is the maximum load time for the mosfet.<br/> - if the mosfet is off, reply message consists of next values b"off {time_since}:{max_load_time}".<br/>All time parameters are in seconds |
|          | b"on[:{working_time}]"         | Turn the load on. Status returns as for b"?"<br/>{working_time} ia an optional parameter and culdn't be higher than currently set maximum activating time for mosfet. If it not so, timeout would be normalized accordingly. If it's equal to "-1", the max_load_time will be used or the time left since time the load started working from.<br/>Reply message the same as for b"?" verb, except the ":{max_load_time}"|
|          | b"off"                         | Turn the load off. Status returns as for b"?" verb, except the ":{max_load_time}" |
|SWITCH    | b"?"                           | Get switch current status.<br/>Reply message consistes of current switch status as b"on" or b"off" followed by period in seconds since it was changed to the current status. The values separated by space.<br/><br/>In case of either timeout was reached or switch/sensor changes its value, the mqtt message would be as for "?" request. |
|          | b"timeout_get"                 | Sends the value of current timeout.<br/>Reply message consists of current timeout value. |
|          | b"timeout_set:{new_timeout}"   | Sets the new value for timer update in seconds. `new_timeout` consists of a new timeout value.<br/>**-1** means there is no timeout and status will return only upon requests or by change event. The reply for this verb will be as for "timeout_get" verb.<br/><br/>*This verb resets the timer if it set up earlier*. |
|SENSOR_I2C| b"?"                           | Updates sensor value and sends it back. Updates timeout as well.<br/> Reply message consists of sensor value and measurement metric separated by space. If there are more than one sensor combined, their values separated by `b":"`|
|          | b"timeout_get"                 | Returns current timeout value and seconds passed since last update separated by space.<br/>**-1** means there is no timeout tracking and update fires only by requests |
|          | b"timeout_set:{new_timeout}"   | Sets new sensor update timeout given in {new_timeout}. Reply message holds new timeout value. This verb clears current timeout |
              

### System calls


Every controller also subscribed for the mqtt topic named as `b"{dev_name}"` and provide reaction for followed verb messages.

|Verb name     | Description                                                     |
|--------------|-----------------------------------------------------------------|
|b"reset"      | Resets the controller                                           |
|b"?"          | Returns the current status of controller<br/>`b"{dev_name}:up time in seconds:keep alive timeout in seconds"`|
|b"get_links"  | Returns the list of mqtt links registered on the controller.<br/>`b"{topic}:tool_type:tool state"`<br/>Tool state differs for diffirent tool types. MOSFET, SWITCH and BUTTON has "on"/"off" statuses. Status of SENSOR_I2C depends on sensor type. Usually it returns last checked state sinse this command doesn't check current status.|
|b"set_kat:{new_timeout}"| Sets new keep alive timeout. Reply message looks as `b"new_kat:{new_timeout}"`|
    
Reply information will be published in mqtt topic `b"{dev_name}/status"`. **dev_name** uses sintax as followed device_XX, where device could be as esp, arduino, attiny and XX is a number. First esp will be named `esp_01`.


### Statuses

All statuses returned on requests use the topics `b{mqtt_link_topic}/status`. It also uses in case of error requests (invalid verb or parameter error).
In case if the requested topic isn't linked to a dedicated tool type or if there is a mistake in verb name the error status will be published on `b"{dev_name}/status"`

Every KEEP_ALIVE_TIMEOUT milliseconds, device sends the signal `b"STEADY:{up time in seconds}"`.
